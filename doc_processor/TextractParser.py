from collections import defaultdict

class BlockType:
    PAGE = "PAGE"

    WORD = "WORD"
    LINE = "LINE"

    KEY_VALUE_SET = "KEY_VALUE_SET"
    SELECTION_ELEMENT = "SELECTION_ELEMENT"

    CELL = "CELL"
    TABLE = "TABLE"


class ResponseKeys:
    BLOCKS = "Blocks"
    BLOCK_TYPE = "BlockType"
    ID = "Id"
    PAGE = "Page"
    CONFIDENCE = "Confidence"
    TEXT = "Text"
    ENTITY_TYPES = "EntityTypes"

    RELATIONSHIPS = "Relationships"
    TYPE = "Type"
    TYPE_CHILD = "CHILD"
    TYPE_VALUE = "VALUE"
    TYPE_KEY = "KEY"
    IDs = "Ids"

    GEOMETRY = "Geometry"
    BOUNDING_BOX = "BoundingBox"
    POLYGON = "Polygon"

    ROW_INDEX = "RowIndex"
    COLUMN_INDEX = "ColumnIndex"

    SELECTION_STATUS = "SelectionStatus"
    SELECTED = "SELECTED"
    NOT_SELECTED = "NOT_SELECTED"

    DOCUMENT_METADATA = "DocumentMetadata"
    PAGES = "Pages"


MIN_CONFIDENCE = 95.0

'''
========================================
=                Location              =
========================================
'''


class BoundingBox:
    '''
    Struct
    ==============
    ### BoudingBox: {
        Width: float
        Height: float
        Left: float
        Top: float
    }
    '''

    def __init__(self, width, height, left, top):
        self._width = width
        self._height = height
        self._left = left
        self._top = top

    def __str__(self):
        return "width: {}, height: {}, left: {}, top: {}".format(self.width, self.height, self.left, self.top)

    @property
    def width(self):
        return self._width

    @property
    def height(self):
        return self._height

    @property
    def left(self):
        return self._left

    @property
    def top(self):
        return self._top


class Vertex:
    '''
    Struct
    ==============
    ### Vertex: {
        x: float
        y: float
    }
    '''

    def __init__(self, x, y):
        self._x = x
        self._y = y

    def __str__(self):
        return "x: {}, y: {}".format(self.x, self.y)

    @property
    def x(self):
        return self._x

    @property
    def y(self):
        return self._y


class Polygon:
    '''
    Struct
    ==============
    ### Polygon: {
        vertices: [class Vertex, ...]
    }
    '''

    def __init__(self, vertices):
        '''
        vertices: list of vertex object
        '''
        self._vertices = vertices

    def __str__(self):
        return "\n".join([str(vertex) for vertex in self.vertices])

    @property
    def vertices(self):
        return self._vertices


class Geometry:
    '''
    Struct
    ==============
    ### Geometry: {
        BoudingBox: Object
        Polygon: Object
    }
    '''

    def __init__(self, geometry):
        '''
        geometry: geometry object from textract response
        '''
        bounding_box = geometry[ResponseKeys.BOUNDING_BOX]
        polygon = geometry[ResponseKeys.POLYGON]
        bb = BoundingBox(bounding_box["Width"], bounding_box["Height"],
                         bounding_box["Left"], bounding_box["Top"])
        vertices = []
        for vertex in polygon:
            vertices.append(Vertex(vertex["X"], vertex["Y"]))

        self._bounding_box = bb
        self._polygon = Polygon(vertices)

    def __str__(self):
        bb = "BoundingBox: {}\n".format(str(self.bounding_box))
        poly = "Polygon: {}\n".format(str(self.polygon))
        return bb + "================" + poly

    @property
    def bounding_box(self):
        return self._bounding_box

    @property
    def polygon(self):
        return self._polygon


'''
========================================
=                 Text                 =
========================================
'''


class Word:
    '''
    Struct
    ==============
    ### Word: {
        block: textract block object with block type "word"
        confidence: textract confidence score
        geometry: geometry object
        id: id of current textract block
        text: text of this word block
    }
    '''

    def __init__(self, block):
        '''
        block: block object from textract response
        '''
        self._block = block
        self._confidence = block[ResponseKeys.CONFIDENCE]
        self._geometry = Geometry(block[ResponseKeys.GEOMETRY])
        self._id = block[ResponseKeys.ID]
        self._text = "" if not block[ResponseKeys.TEXT] else block[ResponseKeys.TEXT]

    def __str__(self):
        return self.text

    @property
    def confidence(self):
        return self._confidence

    @property
    def geometry(self):
        return self._geometry

    @property
    def id(self):
        return self._id

    @property
    def text(self):
        return self._text

    @property
    def block(self):
        return self._block


class Line:
    '''
    Struct
    ==============
    ### Line: {
        block: textract block object with block type "line"
        confidence: textract confidence score
        geometry: geometry object
        id: id of current textract block
        text: text of this line block
        words: list of word object that is children of this Line object
    }
    '''

    def __init__(self, block, block_map):
        '''
        block: textract block object with block type "line"

        block_map: dict that maps block_id to block object
        '''
        self._block = block
        self._confidence = block[ResponseKeys.CONFIDENCE]
        self._geometry = Geometry(block[ResponseKeys.GEOMETRY])
        self._id = block[ResponseKeys.ID]

        self._words = []
        if ResponseKeys.RELATIONSHIPS in block and block[ResponseKeys.RELATIONSHIPS]:
            for relationship in block[ResponseKeys.RELATIONSHIPS]:
                if relationship[ResponseKeys.TYPE] == ResponseKeys.TYPE_CHILD:
                    for child_id in relationship[ResponseKeys.IDs]:
                        if block_map[child_id][ResponseKeys.BLOCK_TYPE] == BlockType.WORD and block_map[child_id][ResponseKeys.CONFIDENCE] >= MIN_CONFIDENCE:
                            self._words.append(Word(block_map[child_id]))
        self._text = " ".join([word.text for word in self._words])

    def __str__(self):
        return self.text

    @property
    def confidence(self):
        return self._confidence

    @property
    def geometry(self):
        return self._geometry

    @geometry.setter
    def geometry(self, value):
        self._geometry = value

    @property
    def id(self):
        return self._id

    @property
    def words(self):
        return self._words

    @words.setter
    def words(self, value):
        self._words = value

    @property
    def text(self):
        return self._text

    @text.setter
    def text(self, value):
        self._text = value

    @property
    def block(self):
        return self._block


class Paragraph:
    '''
    Struct
    ==============
    ### Paragraph: {
        lines: list of line object
        text: text representation of this paragraph
        bounding_box: bounding box of this paragraph (union of line bounding boxes)
    }
    '''

    def __init__(self, lines):
        '''
        lines: list of line objects
        '''
        self._lines = lines
        self._text = ""
        
        # construct the geometry and text for this paragraph
        paragraph_bbox = {
            # this is currently right instead of width, have to minus left value at the end
            "Width": lines[0].geometry.bounding_box.left + lines[0].geometry.bounding_box.width,
            "Height": (lines[-1].geometry.bounding_box.top + lines[-1].geometry.bounding_box.height) - lines[0].geometry.bounding_box.top,
            "Left": lines[0].geometry.bounding_box.left,
            "Top": lines[0].geometry.bounding_box.top
        }
        self._text += (lines[0].text + "\n")
        for line in lines[1:]:
            self._text += (line.text + '\n')
            # update bbox
            paragraph_bbox["Left"] = min(
                paragraph_bbox["Left"], line.geometry.bounding_box.left)
            paragraph_bbox["Width"] = max(paragraph_bbox["Width"], line.geometry.bounding_box.left + line.geometry.bounding_box.width)
        # minus left to get width value
        paragraph_bbox["Width"] -= paragraph_bbox["Left"]

        self._geometry = Geometry({
            ResponseKeys.BOUNDING_BOX: paragraph_bbox,
            ResponseKeys.POLYGON: []
        })

    def __str__(self):
        s = "\n--------- Paragraph ---------\n\n" + \
            self.text + "\n----- [End of Paragraph] -----\n"
        return s

    @property
    def text(self):
        return self._text

    @property
    def lines(self):
        return self._lines

    @property
    def geometry(self):
        return self._geometry


class ParagraphConstructor:
    '''
    this is a pipeline class that creates Paragraph objects with list of Line objects
    '''
    VERTICAL_DIST_MODE = "vertical"
    HORIZONTAL_DIST_MODE = "horizontal"
    HORIZONTAL_DIST_TOLERANCE = 0.01
    VERTICAL_DIST_TOLERANCE = 0.01

    def __init__(self, lines):
        '''
        Parameters:
        =================
        lines: list of Line object
        '''
        # merge lines that is close together by horizontal distance tolerance
        # these lines should be a single line
        new_lines = self._merge_line(lines)

        # get vertical distances between lines
        vert_dist_list = self._get_vertical_dist(new_lines)

        # construct paragraphs
        self._create_paragraph(new_lines, vert_dist_list, upper_lim=self.VERTICAL_DIST_TOLERANCE)

    def _check_vertically_overlap(self, line, column):
        '''
        check if line overlaps a column, if overlap, then that line belongs to that column

        Parameters:
        =================
        line: line object

        column: dict that contain "left" and "right" keys
        '''
        ll = line.geometry.bounding_box.left  # line left
        lr = ll + line.geometry.bounding_box.width  # line right
        cl, cr = column["left"], column["right"]
        return (
            ((lr >= cl) and (lr <= cr)) or
            ((ll >= cl) and (ll <= cr)) or
            ((ll <= cl) and (ll <= lr) and (lr >= cl) and (lr >= cr)) or
            ((cl <= ll) and (cl <= lr) and (cr >= ll) and (cr >= lr))
        )

    def _get_line_readable(self, lines):
        '''
        this method parses list of lines into human readble order (column detection)

        Parameters:
        =================
        lines: list of Line object

        Return:
        =================
        columnIndex2Lines: dict that maps column index to list of lines.
                           Column index is sorted by position of column on document.
                           (upper left the smallest)
        '''
        columns = [] # [column, [lines]]
        for line in lines:
            ll = line.geometry.bounding_box.left  # line left
            lr = ll + line.geometry.bounding_box.width  # line right
            
            column_overlap_count = 0
            for item in columns:
                if self._check_vertically_overlap(line, item[0]):
                    column_overlap_count += 1
            if column_overlap_count >= 2 or column_overlap_count == 0:
                columns.append([
                    {
                        "left": ll,
                        "right": lr
                    },
                    [line]
                ])
            else:
                for index, item in enumerate(columns):
                    if self._check_vertically_overlap(line, item[0]):
                        columns[index][-1].append(line)
                        break
        columnIndex2Lines = defaultdict(list)
        for index, item in enumerate(columns):
            columnIndex2Lines[index] = item[-1]

        return columnIndex2Lines

    def _check_items_same_line(self, item1, item2):
        '''
        check if 2 item belongs to same line in a document using location of bounding box

        Parameters:
        =================
        item: object that has geometry property

        Return:
        =================
        boolean: same line or not
        '''
        bbox1 = item1.geometry.bounding_box
        bbox2 = item2.geometry.bounding_box

        bbox1_top = bbox1.top
        bbox1_bottom = bbox1.top + bbox1.height

        bbox2_top = bbox2.top
        bbox2_bottom = bbox2.top + bbox2.height

        if (
            ((bbox1_bottom >= bbox2_top) and (bbox1_bottom <= bbox2_bottom)) or
            ((bbox1_top <= bbox2_bottom) and (bbox1_top >= bbox2_top)) or
            ((bbox1_top <= bbox2_top) and (bbox1_top <= bbox2_bottom) and (bbox1_bottom >= bbox2_top) and (bbox1_bottom >= bbox2_top)) or
            ((bbox2_top <= bbox1_bottom) and (bbox2_top <= bbox1_top) and (
                bbox2_bottom >= bbox1_bottom) and (bbox2_bottom >= bbox1_top))
        ):
            return True
        return False

    def _merge_geometry(self, geometry1, geometry2):
        '''
        merge 2 geometry vertically

        Parameters:
        =================
        geometry: geometry object
        '''
        new_bbox = {
            "Left": min(geometry1.bounding_box.left, geometry2.bounding_box.left),
            "Top": min(geometry1.bounding_box.top, geometry2.bounding_box.top),
            "Height": max(geometry1.bounding_box.top + geometry1.bounding_box.height, geometry2.bounding_box.top + geometry2.bounding_box.height) - min(geometry1.bounding_box.top, geometry2.bounding_box.top),
            "Width": max(geometry1.bounding_box.left + geometry1.bounding_box.width, geometry2.bounding_box.left + geometry2.bounding_box.width) - min(geometry1.bounding_box.left, geometry2.bounding_box.left)
        }
        return Geometry({
            ResponseKeys.BOUNDING_BOX: new_bbox,
            ResponseKeys.POLYGON: []
        })

    def _merge_line(self, lines):
        '''
        merge all line that belongs to same line location

        Parameters:
        =================
        lines: list of line object

        Return:
        =================
        new_lines: list of lines that are merged
        '''
        if not len(lines):
            return []
        else:
            new_lines = []
            prev_line = lines[0]
            for line in lines[1:]:
                if self._check_items_same_line(prev_line, line):
                    horizontal_dist = self._get_dist(prev_line, line, mode=self.HORIZONTAL_DIST_MODE)
                    if horizontal_dist <= self.HORIZONTAL_DIST_TOLERANCE:
                        # merge 2 lines
                        merged_text = prev_line.text + " " + line.text
                        merged_geometry = self._merge_geometry(
                            prev_line.geometry, line.geometry)
                        prev_line.text = merged_text
                        prev_line.geometry = merged_geometry
                        prev_line.words = prev_line.words + line.words
                else:
                    new_lines.append(prev_line)
                    prev_line = line

            # add the last line
            new_lines.append(prev_line)
            return new_lines

    def _get_dist(self, item1, item2, mode):
        '''
        compute vertical or horizontal distance between 2 items

        Parameters:
        =================
        item: 2 items that has geometry property to compute distance 

        mode: vertical distance or horizontal distance

        Parameters:
        =================
        float: distance between 2 items, range [0, 1]
        '''
        if mode == self.VERTICAL_DIST_MODE:
            bbox_top = item1.geometry.bounding_box
            bbox_bottom = item2.geometry.bounding_box

            bottom_of_bbox_top = bbox_top.top + bbox_top.height
            top_of_bbox_bottom = bbox_bottom.top

            vertical_dist = top_of_bbox_bottom - bottom_of_bbox_top  # float
            return vertical_dist
        elif mode == self.HORIZONTAL_DIST_MODE:
            bbox_left = item1.geometry.bounding_box
            bbox_right = item2.geometry.bounding_box

            right_of_bbox_left = bbox_left.left + bbox_left.width
            left_of_bbox_right = bbox_right.left

            horizontal_dist = left_of_bbox_right - right_of_bbox_left  # float
            return horizontal_dist

    def _get_vertical_dist(self, lines):
        '''
        calculates vertical distance between 2 lines in a column.

        Parameters:
        =================
        lines: list of line object

        Return:
        =================
        vert_dist_list: list of vertical distance between 2 line object.
                        this list has length of len(lines)-1
        '''
        vert_dist_list = []

        prev_line = lines[0]
        for line in lines[1:]:
            if self._check_items_same_line(prev_line, line):
                continue
            vert_dist = self._get_dist(
                prev_line, line, mode=self.VERTICAL_DIST_MODE)
            prev_line = line
            vert_dist_list.append(vert_dist)

        return vert_dist_list

    def _create_paragraph(self, lines, vert_dist_list, upper_lim):
        '''
        create paragraph object from lines

        Parameters:
        =================
        lines: list of line objects
        
        vert_dist_list: list of vertical distance between 2 line object.
                        this list has length of len(lines)-1
        
        upper_lim: vertical distance tolerance. If 2 line object has vertical
                   distance >= upper_lim, then we chunck the lines into 2 paragraphs.
        '''
        self.paragraphs = []
        cur_paragraph_lines = []
        vert_dist_index_fixer = 0
        prev_line = None
        for line_index in range(len(lines)):
            cur_line = lines[line_index]
            vert_dist_index = line_index-1-vert_dist_index_fixer
            if vert_dist_index >= 0:
                if self._check_items_same_line(prev_line, cur_line):
                    cur_paragraph_lines.append(cur_line)
                    vert_dist_index_fixer += 1
                    continue
                vert_dist = vert_dist_list[vert_dist_index]
                # check if outlier detected, truncate the lines into paragraph
                if vert_dist >= upper_lim:
                    # detect columns
                    columnIndex2Lines = self._get_line_readable(
                        cur_paragraph_lines)
                    column_indexes = sorted(list(columnIndex2Lines.keys()))
                    for column_index in column_indexes:
                        self.paragraphs.append(
                            Paragraph(columnIndex2Lines[column_index]))
                    cur_paragraph_lines = []
                
            prev_line = cur_line
            cur_paragraph_lines.append(cur_line)
        
        # finish creating last paragraph
        columnIndex2Lines = self._get_line_readable(cur_paragraph_lines)
        column_indexes = sorted(list(columnIndex2Lines.keys()))
        for column_index in column_indexes:
            self.paragraphs.append(Paragraph(columnIndex2Lines[column_index]))
        


'''
========================================
=                 FORM                 =
========================================
'''


class SelectionElement:
    '''
    Struct
    ==============
    ### SelectionElement: {
        confidence: textract confidence score
        geometry: geometry object
        id: id of current textract block
        selection_status: string ["SELECTED" | "NOT_SELECTED"]
    }
    '''

    def __init__(self, block):
        '''
        block: textract block object with block type "SelectionElement"
        '''
        self._confidence = block[ResponseKeys.CONFIDENCE]
        self._geometry = Geometry(block[ResponseKeys.GEOMETRY])
        self._id = block[ResponseKeys.ID]
        self._selection_status = block[ResponseKeys.SELECTION_STATUS]

    @property
    def confidence(self):
        return self._confidence

    @property
    def geometry(self):
        return self._geometry

    @property
    def id(self):
        return self._id

    @property
    def selection_status(self):
        return self._selection_status


class FieldKey:
    '''
    Struct
    ==============
    ### FieldKey: {
        block: textract block object with block type "key_value_set" and entity type "key"
        confidence: textract confidence score
        geometry: geometry object
        id: id of current textract block
        content: list of word object for current key
        text: str for the list of word object in content
    }

    ### Textract Resposne:
        Block: {
            "BlockType": "KEY_VALUE_SET"
            "EntityTypes": ["KEY"]
            "Relationships": [
                { "Type": "VALUE", "Ids": ["c4db598d-c0b1-4e1f-ace2-508af8347f92"] },
                {
                    "Type": "CHILD",
                    "Ids": [
                        "35e94322-853f-4070-a417-b1c6c9cdccec",
                        "3c9229ab-742a-4c11-8186-3b8c807aab85"
                    ]
                }
            ]
        }
    '''

    def __init__(self, block, child_ids, block_map):
        '''
        block: textract block object with block type "KeyValueSet" and entity type of "KEY"

        child_ids: list of child ids

        block_map: dict that maps block_id to block object
        '''
        self._block = block
        self._confidence = block[ResponseKeys.CONFIDENCE]
        self._geometry = Geometry(block[ResponseKeys.GEOMETRY])
        self._id = block[ResponseKeys.ID]

        self._content = []
        text_list = []
        for child_id in child_ids:
            child_block = block_map[child_id]
            if child_block[ResponseKeys.BLOCK_TYPE] == BlockType.WORD:
                word = Word(child_block)
                self._content.append(word)
                text_list.append(word.text)

        self._text = ' '.join(text_list) if len(text_list) else ""

    def __str__(self):
        return self.text

    @property
    def confidence(self):
        return self._confidence

    @property
    def geometry(self):
        return self._geometry

    @property
    def id(self):
        return self._id

    @property
    def content(self):
        return self._content

    @property
    def text(self):
        return self._text

    @property
    def block(self):
        return self._block


class FieldValue:
    '''
    Struct
    ==============
    ### FieldValue: {
        block: textract block object with block type "key_value_set" and entity type "value"
        confidence: textract confidence score
        geometry: geometry object
        id: id of current textract block
        content: list of word object for current or selection status
        text: str for the list of word object in content or selection status
    }

    ### Textract Resposne:
        Block: {
            "BlockType": "KEY_VALUE_SET"
            "EntityTypes": ["VALUE"]
            "Relationships": [
                {
                    "Type": "CHILD",
                    "Ids": [
                        "35e94322-853f-4070-a417-b1c6c9cdccec", --> SelectionStatus": "NOT_SELECTED"
                        "3c9229ab-742a-4c11-8186-3b8c807aab85"
                    ]
                }
            ]
        }
    '''

    def __init__(self, block, child_ids, block_map):
        '''
        block: textract block object with block type "KeyValueSet" and entity type of "VALUE"

        child_ids: list of child ids

        block_map: dict that maps block_id to block object
        '''
        self._block = block
        self._confidence = block[ResponseKeys.CONFIDENCE]
        self._geometry = Geometry(block[ResponseKeys.GEOMETRY])
        self._id = block[ResponseKeys.ID]

        self._content = []
        text_list = []
        for child_id in child_ids:
            child_block = block_map[child_id]
            if child_block[ResponseKeys.BLOCK_TYPE] == BlockType.WORD:
                word = Word(child_block)
                self._content.append(word)
                text_list.append(word.text)
            elif child_block[ResponseKeys.BLOCK_TYPE] == BlockType.SELECTION_ELEMENT:
                selection_element = SelectionElement(child_block)
                self._content.append(selection_element)
                text_list.append(selection_element.selection_status)
        self._text = " ".join(text_list) if len(text_list) else ""

    def __str__(self):
        return self.text

    @property
    def confidence(self):
        return self._confidence

    @property
    def geometry(self):
        return self._geometry

    @property
    def id(self):
        return self._id

    @property
    def content(self):
        return self._content

    @property
    def text(self):
        return self._text

    @property
    def block(self):
        return self._block


class KeyValueSet:
    '''
    Struct
    ==============
    ### KeyValueSet: {
        key: FieldKey object
        value: FieldValue object
    }
    '''

    def __init__(self, block, block_map):
        '''
        block: a textract block that has block type of KEY_VALUE_SET
        '''
        self._key = None
        self._value = None

        for item in block[ResponseKeys.RELATIONSHIPS]:
            item_type = item[ResponseKeys.TYPE]
            if item_type == ResponseKeys.TYPE_CHILD:
                self._key = FieldKey(block, item[ResponseKeys.IDs], block_map)
            elif item_type == ResponseKeys.TYPE_VALUE:
                for child_id in item[ResponseKeys.IDs]:
                    child_block = block_map[child_id]
                    if ResponseKeys.TYPE_VALUE in child_block[ResponseKeys.ENTITY_TYPES] and ResponseKeys.RELATIONSHIPS in child_block:
                        for child_block_item in child_block[ResponseKeys.RELATIONSHIPS]:
                            if child_block_item[ResponseKeys.TYPE] == ResponseKeys.TYPE_CHILD:
                                self._value = FieldValue(
                                    child_block, child_block_item[ResponseKeys.IDs], block_map)

    def __str__(self):
        k = ""
        v = ""
        if(self.key):
            k = str(self.key)
        if(self.value):
            v = str(self.value)
        s = "Key: {}\nValue: {}".format(k, v)
        return s

    @property
    def key(self):
        return self._key

    @property
    def value(self):
        return self._value


class Form:
    '''
    Struct
    ==============
    ### Form: {
        key_value_sets: list of KeyValueSet object
        key_value_set_map: maps key.text to KeyValueSet object
    }
    '''

    def __init__(self):
        self._key_value_sets = []
        self._key_value_set_map = {}

    def __str__(self):
        s = "\n\n======= Form =======\n\n"
        for kv_set in self.key_value_sets:
            s += (str(kv_set) + "\n\n")
        s += "===== End of Form =====\n\n"
        return s

    @property
    def key_value_sets(self):
        return self._key_value_sets

    @property
    def key_value_set_map(self):
        return self._key_value_set_map

    def add_key_val_set(self, key_val_set):
        '''
        kay_val_set: KeyValueSet object
        '''
        self._key_value_sets.append(key_val_set)
        self._key_value_set_map[key_val_set.key.text] = key_val_set

    def get_kv_set_by_key(self, key):
        '''
        key: text of a FieldKey object
        '''
        kv_set = None if key not in self.key_value_set_map else self.key_value_set_map[key]
        return kv_set

    def search_kv_set_by_key(self, key):
        '''
        get the KeyValueSet objects that has parameter key
        '''
        search_key = key.lower()
        results = []
        for kv_set in self.key_value_sets:
            if search_key in kv_set.key.text.lower():
                results.append(kv_set)
        return results


'''
========================================
=                 Table                =
========================================
'''


class Cell:
    '''
    Struct
    ==============
    ### Cell: {
        block: textract block object with block type "cell"
        confidence: textract confidence score
        geometry: geometry object
        row_index: starting with 1, the row postion of current cell in table
        column_index: starting with 1, the column posistion of current cell in table
        id: id of current textract block
        content: Word and SelectionElement children object
        text: str representation
    }
    '''

    def __init__(self, block, block_map):
        '''
        block: textract block object with block type "CELL"

        block_map: dict that maps block_id to block object
        '''
        self._block = block
        self._confidence = block[ResponseKeys.CONFIDENCE]
        self._row_index = block[ResponseKeys.ROW_INDEX]
        self._column_index = block[ResponseKeys.COLUMN_INDEX]
        self._geometry = Geometry(block[ResponseKeys.GEOMETRY])
        self._id = block[ResponseKeys.ID]
        self._text = ""

        self._content = []
        if ResponseKeys.RELATIONSHIPS in block and block[ResponseKeys.RELATIONSHIPS]:
            for relationship in block[ResponseKeys.RELATIONSHIPS]:
                if relationship[ResponseKeys.TYPE] == ResponseKeys.TYPE_CHILD:
                    for child_id in relationship[ResponseKeys.IDs]:
                        child_block = block_map[child_id]
                        child_block_type = child_block[ResponseKeys.BLOCK_TYPE]
                        if child_block_type == BlockType.WORD:
                            word = Word(child_block)
                            self._content.append(word)
                            self._text += (word.text + " ")
                        elif child_block_type == BlockType.SELECTION_ELEMENT:
                            selection_element = SelectionElement(child_block)
                            self._content.append(selection_element)
                            self._text += (selection_element.selection_status + ", ")

    def __str__(self):
        return self.text

    @property
    def confidence(self):
        return self._confidence

    @property
    def row_index(self):
        return self._row_index

    @property
    def column_index(self):
        return self._column_index

    @property
    def geometry(self):
        return self._geometry

    @property
    def id(self):
        return self._id

    @property
    def content(self):
        return self._content

    @property
    def text(self):
        return self._text

    @property
    def block(self):
        return self._block


class Row:
    '''
    Struct
    ==============
    ### Row: {
        cells: list of cell object in table
    }
    '''

    def __init__(self):
        self._cells = []

    def __str__(self):
        s = ""
        for cell in self.cells:
            s += "[{}]".format(str(cell))
        return s

    @property
    def cells(self):
        return self._cells

    def add_cell(self, cell):
        self.cells.append(cell)


class Table:
    '''
    Struct
    ==============
    ### Table: {
        block: textract block object with block type "table"
        confidence: textract confidence score
        geometry: geometry object
        id: id of current textract block
        rows: list of row objects
    }
    '''

    def __init__(self, block, block_map):
        '''
        block: textract repsonse of block type "TABLE"

        block_map: dict that maps block_id to block object
        '''
        self._block = block
        self._confidence = block[ResponseKeys.CONFIDENCE]
        self._geometry = Geometry(block[ResponseKeys.GEOMETRY])
        self._id = block[ResponseKeys.ID]
        self._rows = []
        # maps column index to longest str in that column for pretty printing
        self._columnIndex2Longest = defaultdict(lambda: 0)
        cur_row_index = 1
        row = Row()
        cell = None

        # looking into child_ids in this block
        if ResponseKeys.RELATIONSHIPS in block and block[ResponseKeys.RELATIONSHIPS]:
            for relationship in block[ResponseKeys.RELATIONSHIPS]:
                if relationship[ResponseKeys.TYPE] == ResponseKeys.TYPE_CHILD:
                    for child_id in relationship[ResponseKeys.IDs]:
                        # if cell is in current row index, add it to row object
                        # else create new row wtih row index +1
                        cell = Cell(block_map[child_id], block_map)
                        if cell.row_index > cur_row_index:
                            self._rows.append(row)
                            row = Row()
                            cur_row_index = cell.row_index
                        self._columnIndex2Longest[cell.column_index] = max(
                            len(cell.text), self._columnIndex2Longest[cell.column_index])
                        row.add_cell(cell)
                    if len(row.cells):
                        self._rows.append(row)

    def __str__(self):
        s = "\n\n======= [Table] =======\n\n"
        for row in self.rows:
            for cell in row.cells:
                cell_col_index = cell.column_index
                text_padded = cell.text + \
                    (" " *
                     (self._columnIndex2Longest[cell_col_index]-len(cell.text)))
                s += text_padded
            s += "\n"
        s += "===== [End of Table] =====\n\n"
        return s

    def get_table_readable(self):
        # returns table in human readable format as str
        pass

    @property
    def confidence(self):
        return self._confidence

    @property
    def geometry(self):
        return self._geometry

    @property
    def id(self):
        return self._id

    @property
    def rows(self):
        return self._rows

    @property
    def block(self):
        return self._block


'''
========================================
=               Document               =
========================================
'''


class Page:
    '''
    Struct
    ==============
    ### Page: {
        blocks: textract blocks list (contains all blocks in a page)
        lines: list of line objects
        paragraphs: list of paragraph object
        form: form object
        tables: list of table object
        content: (line, form, table) objects in same order as block show up in textract response
        text: text of current page (not containing table and form)
        page_num: page number of current page object
    }
    '''

    def __init__(self, page_num, blocks, block_map, non_line_childs):
        '''
        page_num: the page number of this Page object 

        block: textract block object with block type "PAGE"

        block_map: dict that maps block_id to block object

        non_line_childs: list of child_ids that belongs to TABLE or FORM
        '''
        self._blocks = blocks
        self._text = ""
        self._lines = []
        self._form = Form()
        self._tables = []
        self._content = []
        self._page_num = page_num

        self._parse(block_map, non_line_childs)

    def __str__(self):
        s = "\n***************** [Page Number: " + \
            str(self.page_num) + "] ********************\n"
        for item in self.content:
            s += (str(item) + "\n")
        s += "\n***************** [End of Page " + \
            str(self.page_num) + "] ********************\n"
        return s

    def _parse(self, block_map, non_line_childs):
        '''
        parse blocks list into defined objects

        Parameters:
        =================
        non_line_childs: list of child ids that belongs to table or form

        block_map: dict that maps block id to block object
        '''
        for block in self.blocks:
            block_type = block[ResponseKeys.BLOCK_TYPE]
            if block_type == BlockType.PAGE:
                self._geometry = Geometry(block[ResponseKeys.GEOMETRY])
                self._id = block[ResponseKeys.ID]
            elif block_type == BlockType.LINE:
                # if words belongs to table or form, then dont add to line object
                if ResponseKeys.RELATIONSHIPS in block:
                    for relationship in block[ResponseKeys.RELATIONSHIPS]:
                        child_ids = relationship[ResponseKeys.IDs]
                        if not all(child_id in non_line_childs for child_id in child_ids):
                            line = Line(block, block_map)
                            self.add_line(line)
                            # self.add_content(line)
                            # self._text += (line.text + '\n')
            elif block_type == BlockType.TABLE:
                table = Table(block, block_map)
                self.add_table(table)
                self.add_content(table)
            elif block_type == BlockType.KEY_VALUE_SET:
                if ResponseKeys.TYPE_KEY in block[ResponseKeys.ENTITY_TYPES]:
                    kv_set = KeyValueSet(block, block_map)
                    if kv_set.key:
                        self.form.add_key_val_set(kv_set)
                        # self.add_content(kv_set)
        if len(self.form.key_value_sets):
            self.add_content(self.form)

        self._paragraphs = []
        if len(self.lines):
            # parse lines to paragraphs
            self._paragraphs = ParagraphConstructor(self.lines).paragraphs
            # concat paragraphs and other contents
            self._content = self._paragraphs + self._content
        
        for paragraph in self._paragraphs:
            self._text += (paragraph.text + "\n")

    @property
    def blocks(self):
        return self._blocks

    @property
    def text(self):
        return self._text

    @property
    def lines(self):
        return self._lines

    @property
    def paragraphs(self):
        return self._paragraphs

    @property
    def form(self):
        return self._form

    @property
    def tables(self):
        return self._tables

    @property
    def content(self):
        return self._content

    @property
    def geometry(self):
        return self._geometry

    @property
    def id(self):
        return self._id

    @property
    def page_num(self):
        return self._page_num

    def add_line(self, line):
        '''
        add line to lines list

        Parameters:
        =================
        line: line object
        '''
        self.lines.append(line)

    def add_content(self, item):
        '''
        add item to content list

        Parameters:
        =================
        item: any object defined above
        '''
        self.content.append(item)

    def add_table(self, table):
        '''
        add table to tables list

        Parameters:
        =================
        table: table object
        '''
        self.tables.append(table)


class Document:
    '''
    Struct
    ==============
    ### Document: {
        total_pages: total number of pages in this document
        pageNum2Block: dict that maps page number to all blocks in that page
        block_map: dict that maps block_id to block object
        doc_pages: list that contains Page objects
    }
    '''

    def __init__(self, json_response_list, doc_name=None):
        '''
        Parameters:
        =================
        json_response_list: list of json responses returned from textract

        doc_name: name of current document
        '''
        self._doc_name = doc_name

        if not isinstance(json_response_list, list):
            json_response_list = [json_response_list]

        self._total_pages = json_response_list[0][ResponseKeys.DOCUMENT_METADATA][
            ResponseKeys.PAGES] if ResponseKeys.PAGE in json_response_list[0][ResponseKeys.BLOCKS][0] else len(json_response_list)

        # organize json by page
        self._organize_by_page(json_response_list)
        # parse each page
        self._parse()

    def _organize_by_page(self, json_response_list):
        '''
        create a dict that maps page_num to all blocks that belongs to that page

        Parameters:
        =================
        json_response_list: list of json response returned by textract
        '''
        blocks_concat = []
        for json_res in json_response_list:
            blocks_concat += json_res[ResponseKeys.BLOCKS]

        self._pageNum2Blocks = {}  # maps page number to all blocks in that page
        cur_page_num = 1
        cur_block_list = []
        for block in blocks_concat:
            if block[ResponseKeys.BLOCK_TYPE] == BlockType.PAGE and len(cur_block_list):
                self._pageNum2Blocks[cur_page_num] = cur_block_list
                cur_block_list = []
                cur_page_num += 1
            cur_block_list.append(block)
        self._pageNum2Blocks[cur_page_num] = cur_block_list

    def _parse(self):
        '''
        create a Page object for each page in this document
        '''
        self._non_line_childs = []
        self._block_map = {}  # maps block id to corresponding block

        special_block_types = [BlockType.KEY_VALUE_SET,
                               BlockType.SELECTION_ELEMENT, BlockType.CELL, BlockType.TABLE]
        page_nums = list(range(1, self.total_pages+1))
        for page_num in page_nums:
            blocks = self.get_blocks_by_page_num(page_num)
            for block in blocks:
                if ResponseKeys.BLOCK_TYPE in block and ResponseKeys.ID in block:
                    self.add_block_by_id(block[ResponseKeys.ID], block)
                    if block[ResponseKeys.BLOCK_TYPE] in special_block_types and ResponseKeys.RELATIONSHIPS in block:
                        for relationship in block[ResponseKeys.RELATIONSHIPS]:
                            self._non_line_childs.extend(
                                relationship[ResponseKeys.IDs])

        self._doc_pages = []  # list of Page object
        for page_num in page_nums:
            self.add_page(Page(page_num, self.get_blocks_by_page_num(
                page_num), self.block_map, self.non_line_childs))

    def __str__(self):
        doc_header = f"Document: {self.doc_name}" if self.doc_name else "Document"
        s = f"\n=================== [{doc_header}] ======================\n"
        for page in self.doc_pages:
            s += (str(page) + "\n\n")
        s += "==================== [End of Document] =====================\n"
        return s

    @property
    def total_pages(self):
        return self._total_pages

    @property
    def pageNum2Blocks(self):
        return self._pageNum2Blocks

    def get_blocks_by_page_num(self, page_num):
        '''
        get list of blocks by page number

        Parameters:
        =================
        page_num: (int) page number of blocks you want to get
        '''
        if page_num in self.pageNum2Blocks.keys():
            return self.pageNum2Blocks[page_num]
        else:
            return None

    @property
    def block_map(self):
        return self._block_map

    def add_block_by_id(self, block_id, block):
        '''
        add key value pair (block_id, block) to block_map

        Parameters:
        =================
        block_id: id of current block

        block: block object
        '''
        self.block_map[block_id] = block

    @property
    def doc_pages(self):
        return self._doc_pages

    def add_page(self, page_obj):
        '''
        add page object to doc_pages list

        Parameters:
        =================
        page_obj: a page object
        '''
        self.doc_pages.append(page_obj)

    def get_page_by_page_num(self, page_num):
        '''
        get page object by page number

        Parameters:
        =================
        page_num: (int) page number of page object you want to get
        '''
        return self.doc_pages[page_num]

    @property
    def non_line_childs(self):
        return self._non_line_childs

    @property
    def doc_name(self):
        return self._doc_name

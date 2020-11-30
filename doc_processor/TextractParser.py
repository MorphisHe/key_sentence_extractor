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
        self._text = "" if not block[ResponseKeys.TEXT] else block[ResponseKeys.TEXT]

        self._words = []
        if ResponseKeys.RELATIONSHIPS in block and block[ResponseKeys.RELATIONSHIPS]:
            for relationship in block[ResponseKeys.RELATIONSHIPS]:
                if relationship[ResponseKeys.TYPE] == ResponseKeys.TYPE_CHILD:
                    for child_id in relationship[ResponseKeys.IDs]:
                        if block_map[child_id][ResponseKeys.BLOCK_TYPE] == BlockType.WORD:
                            self._words.append(Word(block_map[child_id]))

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
    def words(self):
        return self._words

    @property
    def text(self):
        return self._text

    @property
    def block(self):
        return self._block


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
                self._text = selection_element.selection_status
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
        self._columnIndex2Longest = defaultdict(lambda: 0) # maps column index to longest str in that column for pretty printing
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
                        self._columnIndex2Longest[cell.column_index] = max(len(cell.text), self._columnIndex2Longest[cell.column_index])
                        row.add_cell(cell)
                    if len(row.cells):
                        self._rows.append(row)

    def __str__(self):
        s = "\n\n======= Table =======\n\n"
        for row in self.rows:
            for cell in row.cells:
                cell_col_index = cell.column_index
                text_padded = cell.text + (" " * (self._columnIndex2Longest[cell_col_index]-len(cell.text)))
                s += text_padded
            s += "\n"
        s += "===== End of Table =====\n\n"
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
        s = "\n***************** Page Number: " + str(self.page_num) + " ********************\n"
        for item in self.content:
            s += (str(item) + "\n")
        s += "\n***************** End of Page " + str(self.page_num) + " ********************\n"
        return s

    def _parse(self, block_map, non_line_childs):
        '''
        parse blocks list into defined objects

        non_line_childs: list of child ids that belongs to table or form
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
                            self.add_content(line)
                            self._text += (line.text + '\n')
            elif block_type == BlockType.TABLE:
                table = Table(block, block_map)
                self.add_table(table)
                self.add_content(table)
            elif block_type == BlockType.KEY_VALUE_SET:
                if ResponseKeys.TYPE_KEY in block[ResponseKeys.ENTITY_TYPES]:
                    kv_set = KeyValueSet(block, block_map)
                    if kv_set.key:
                        self.form.add_key_val_set(kv_set)
                        #self.add_content(kv_set)
        if len(self.form.key_value_sets):
            self.add_content(self.form)

    def get_lines_readable(self):
        '''
        TODO
        return lines of current page in readable order (column and row organized)
        '''
        columns = []
        lines = []
        for item in self.lines:
            column_found = False
            for index, column in enumerate(columns):
                bbox_left = item.geometry.bounding_box.left
                bbox_right = item.geometry.bounding_box.left + item.geometry.bounding_box.width
                bbox_centre = item.geometry.bounding_box.left + item.geometry.bounding_box.width/2
                column_centre = column['left'] + column['right']/2
                if (bbox_centre > column['left'] and bbox_centre < column['right']) or (column_centre > bbox_left and column_centre < bbox_right):
                    # Bbox appears inside the column
                    lines.append([index, item.text])
                    column_found = True
                    break
            if not column_found:
                columns.append({'left': item.geometry.bounding_box.left,
                                'right': item.geometry.bounding_box.left + item.geometry.bounding_box.width})
                lines.append([len(columns)-1, item.text])

        lines.sort(key=lambda x: x[0])
        return lines

    def get_text_readable(self):
        # TODO
        lines = self.get_lines_readable()
        text = ""
        for line in lines:
            text = text + line[1] + '\n'
        return text

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
        self.lines.append(line)

    def add_content(self, item):
        self.content.append(item)

    def add_table(self, table):
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
        json_response_list: list of json responses returned from textract
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

        special_block_types = [BlockType.KEY_VALUE_SET, BlockType.SELECTION_ELEMENT, BlockType.CELL, BlockType.TABLE]
        page_nums = list(range(1, self.total_pages+1))
        for page_num in page_nums:
            blocks = self.get_blocks_by_page_num(page_num)
            for block in blocks:
                if ResponseKeys.BLOCK_TYPE in block and ResponseKeys.ID in block:
                    self.add_block_by_id(block[ResponseKeys.ID], block)
                    if block[ResponseKeys.BLOCK_TYPE] in special_block_types and ResponseKeys.RELATIONSHIPS in block:
                        for relationship in block[ResponseKeys.RELATIONSHIPS]:
                            self._non_line_childs.extend(relationship[ResponseKeys.IDs])

        self._doc_pages = []  # list of Page object
        for page_num in page_nums:
            self.add_page(Page(page_num, self.get_blocks_by_page_num(page_num), self.block_map, self.non_line_childs))

    def __str__(self):
        doc_header = f"Document: {self.doc_name}" if self.doc_name else "Document"
        s = f"\n{doc_header}\n==========================================\n"
        for page in self.doc_pages:
            s += (str(page) + "\n\n")
        s += "==========================================\n"
        return s

    @property
    def total_pages(self):
        return self._total_pages

    @property
    def pageNum2Blocks(self):
        return self._pageNum2Blocks

    def get_blocks_by_page_num(self, page_num):
        if page_num in self.pageNum2Blocks.keys():
            return self.pageNum2Blocks[page_num]
        else:
            return None

    @property
    def block_map(self):
        return self._block_map

    def add_block_by_id(self, block_id, block):
        self.block_map[block_id] = block

    @property
    def doc_pages(self):
        return self._doc_pages

    def add_page(self, page_obj):
        self.doc_pages.append(page_obj)

    def get_page_by_page_num(self, page_num):
        return self.doc_pages[page_num]

    @property
    def non_line_childs(self):
        return self._non_line_childs

    @property
    def doc_name(self):
        return self._doc_name
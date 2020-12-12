import time
import sys

import boto3
import concurrent.futures

import tempfile
from io import BytesIO
from pdf2image import convert_from_bytes


class SupportedFiles:
    '''
    Enum type class for supported file formats
    '''
    JPEG = "jpeg"
    JPG = "jpg"
    PNG = "png"
    PDF = "pdf"

class ProcessType:
    '''
    Enum type class for textract process type
    '''
    DETECTION = "DETECTION"
    ANALYSIS = "ANALYSIS"



class SingleDocumentProcessor:
    '''
    This class process a single s3 pdf document by converting pages into image then extract information from it
    This class also gets information from s3 image objects
    '''
    _textract = boto3.client("textract")
    _pageNum2BytesArr = {} # dict mapping page number to corresponding bytes array
    _image_mode = False # indicating whether or not we dealing with image input

    def __init__(self, s3_obj, process_type):
        if process_type in [ProcessType.DETECTION, ProcessType.ANALYSIS]:
            self.process_type = process_type
        else:
            raise Exception(
                f"Invalid Process Type: {process_type}\nUse only: {ProcessType.DETECTION}, {ProcessType.ANALYSIS}")
        doc_name = s3_obj.key
        doc_extension = doc_name.split(".")[-1].lower()
        print(f"Starting Processing Document: {doc_name}")
        if doc_extension == SupportedFiles.PDF:
            with tempfile.TemporaryDirectory() as temp_dir:
                imgs = convert_from_bytes(s3_obj.get()["Body"].read(), thread_count=100,
                                        output_folder=temp_dir, fmt="png", grayscale=True)
                page_nums = list(range(1, len(imgs)+1))
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    executor.map(self._image_to_bytes, imgs, page_nums)
        elif doc_extension in [SupportedFiles.JPEG, SupportedFiles.JPG, SupportedFiles.PNG]:
            self._image_mode = True
            self._bucket_name = s3_obj.bucket_name
            self._doc_name = s3_obj.key
        else:
            raise Exception(f"Invalid Document Format: {doc_extension}\nUse only: {SupportedFiles.JPEG}, {SupportedFiles.JPG}, {SupportedFiles.PNG}, {SupportedFiles.PDF}")

    def _image_to_bytes(self, img, page_num):
        '''
        converts image to bytes

        Parameters:
        =================
        img: img from img2pdf library output

        page_num: page number of that img
        '''
        byte_arr = BytesIO()
        img.save(byte_arr, format='PNG')
        self.pageNum2BytesArr[page_num] = byte_arr.getvalue()
        print(f"Done Converting Page #: {page_num}")

    def _get_single_page_results(self, page_num):
        '''
        get the detection result of a single page

        Paramters:
        =================
        page_num: page number of pdf to perform detection

        return:
        =================
        page_num: page number of pdf that is detected

        response: aws textract response
        '''
        response = None
        if self.process_type == ProcessType.DETECTION:
            response = self.textract.detect_document_text(
                Document={
                    "Bytes": self.pageNum2BytesArr[page_num]
                }
            )
        elif self.process_type == ProcessType.ANALYSIS:
            response = self.textract.analyze_document(
                Document={
                    "Bytes": self.pageNum2BytesArr[page_num]
                },
                FeatureTypes=["TABLES", "FORMS"]
            )

        print(f"Done Extracting Information From Page #{page_num}")
        return (page_num, response)

    def get_results(self):
        '''
        get detection results from all pages of pdf or image

        return:
        =================
        results: list of textract response in page number accending order
        '''
        if self.image_mode:
            response = None
            if self.process_type == ProcessType.DETECTION:
                response = self.textract.detect_document_text(
                    Document={
                        "S3Object": {
                            "Bucket": self._bucket_name,
                            "Name": self._doc_name
                        }
                    }
                )
            elif self.process_type == ProcessType.ANALYSIS:
                response = self.textract.analyze_document(
                    Document={
                        "S3Object": {
                            "Bucket": self._bucket_name,
                            "Name": self._doc_name
                        }
                    },
                    FeatureTypes=["TABLES", "FORMS"]
                )
            return [response]
        else:
            # pdf mode
            pageNum2Result = {}
            max_sim_calls = 5 # max same time call allowed for aws textract
            page_nums = list(self.pageNum2BytesArr.keys())
            cur_page_nums_slice = page_nums[:max_sim_calls]
            cur_right_index = max_sim_calls
            while len(cur_page_nums_slice):
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    results = executor.map(self._get_single_page_results, cur_page_nums_slice)
                for res in results:
                    pageNum2Result[res[0]] = res[1]
                cur_page_nums_slice = page_nums[cur_right_index : cur_right_index+max_sim_calls]
                cur_right_index += max_sim_calls

            self._clear_memory()
            results = [pageNum2Result[page_num] for page_num in sorted(list(pageNum2Result.keys()))]
            return results

    def _clear_memory(self):
        '''
        free the memory of current object
        '''
        self._pageNum2BytesArr = {}
    
    @property
    def textract(self):
        return self._textract

    @property
    def pageNum2BytesArr(self):
        return self._pageNum2BytesArr
    
    @property
    def image_mode(self):
        return self._image_mode




class BatchDocumentProcessor:
    '''
    This class able to process multiple s3 documents using multithreads
    '''

    _textract = boto3.client("textract")
    job_ids = []
    jobId2DocName = {} # map job_id to document name
    jobId2ProcessType = {} # map job_id to process type
    jobId2TextractFunc = {} # map job_id to textract function (Detection | Analysis)
    jobId2ResponseList = {} # map job_id to list of textract response

    def start_textract_job(self, s3_bucket_name, s3_doc_name_list, process_type_list):
        '''
        Start textract job for multiple pdf document in s3 bucket

        Parameters:
        =================
        s3_bucket_name: name of the s3 bucket

        s3_doc_name_list: list of s3 document

        process_type_list: list of process type for each of the s3_documents
        '''
        docName_ProcType_zip = list(zip(s3_doc_name_list, process_type_list))
        for s3_doc_name, process_type in docName_ProcType_zip:
            response = None
            if process_type == ProcessType.DETECTION:
                response = self.textract.start_document_text_detection(
                    DocumentLocation={
                        "S3Object": {
                            "Bucket": s3_bucket_name,
                            "Name": s3_doc_name
                        }
                    }
                )
            elif process_type == ProcessType.ANALYSIS:
                response = self.textract.start_document_analysis(
                    DocumentLocation={
                        "S3Object": {
                            "Bucket": s3_bucket_name,
                            "Name": s3_doc_name
                        }
                    },
                    FeatureTypes=["TABLES", "FORMS"]
                )
            self.job_ids.append(response["JobId"])
            self.jobId2DocName[self.job_ids[-1]] = s3_doc_name
            print(f"Starting Job for: {s3_doc_name}")

            if process_type in [ProcessType.DETECTION, ProcessType.ANALYSIS]:
                self.jobId2ProcessType[self.job_ids[-1]] = process_type
                self.jobId2TextractFunc[self.job_ids[-1]] = self.textract.get_document_text_detection if process_type == ProcessType.DETECTION else self.textract.get_document_analysis
            else:
                raise Exception(
                    f"Invalid Process Type: {process_type}\nUse only: {ProcessType.DETECTION}, {ProcessType.ANALYSIS}")


    def _check_job_status(self, job_id):
        '''
        Listen to textract job with job_id

        Parameters:
        =================
        job_id: job_id of the textract job to listen to

        Return:
        =================
        job_id: job_id of the job that finished

        status: status of the finished job
        '''
        s = time.time()
        job_doc_name = self.jobId2DocName[job_id]
        response = self.jobId2TextractFunc[job_id](JobId=job_id)
        status = response["JobStatus"]
        print(f"Start Listening to Job: {job_doc_name}\nCurrent Job Status: {status}")

        while status == "IN_PROGRESS":
            time.sleep(5)
            response = self.jobId2TextractFunc[job_id](JobId=job_id)
            status = response["JobStatus"]
            print(f"Job {job_doc_name} Status: {status}")
            sys.stdout.flush()
        e = time.time()
        print(f"\nJob: {job_doc_name} Done!\nJob Status: {status}\nTotal Time Used: {e-s} Seconds.\n")
        return (job_id, status)


    def _get_single_doc_results(self, job_id, status):
        '''
        Extract responses from a finished job

        Parameters:
        =================
        job_id: job_id of the textract job to get results

        status: status of the response from _check_job_status function

        Return:
        =================
        job_id: job_id of the job that finished

        res_list: list of the json response that is extracted
        '''
        s = time.time()
        job_doc_name = self.jobId2DocName[job_id]
        if status == "SUCCEEDED":
            print(f"\nGetting Results For Job: {job_doc_name}")
            response = self.jobId2TextractFunc[job_id](JobId=job_id)
            res_list = [response]
            next_token = None if "NextToken" not in response else response["NextToken"]
            
            while next_token:
                response = self.jobId2TextractFunc[job_id](JobId=job_id, NextToken=next_token)
                res_list.append(response)
                next_token = None if "NextToken" not in response else response["NextToken"]
            e = time.time()
            print(f"Done Getting Results For Job: {job_doc_name}")
            print("Results Received For", response["DocumentMetadata"]["Pages"], "Pages.")
            print(f"Total Time Used For Getting Results: {e-s} Seconds.\n")
            return (job_id, res_list)
        else:
            raise Exception(f"Job {job_id} Failed With Status: {status}.")

    def get_results(self):
        '''
        Extract results from all documents that is processed

        Return:
        =================
        docName2Result: dict that maps document name to list of json responses extracted
        '''
        # listen to job status using multithreading
        with concurrent.futures.ThreadPoolExecutor() as executor:
            # reuslts is list of tuples (job_id, status)
            results = executor.map(self._check_job_status, self.job_ids)

        job_id_list = []
        status_list = []
        for res in results:
            job_id_list.append(res[0])
            status_list.append(res[1])
        # get results using multithreading
        with concurrent.futures.ThreadPoolExecutor() as executor:
            # reuslts is list of tuples (job_id, res_list)
            # res_list contains multiple response for job_id
            results = executor.map(self._get_single_doc_results, job_id_list, status_list)

        docName2Result = {self.jobId2DocName[result[0]] : result[1] for result in results}
        print("All Done")
        self._clear_memory()

        return docName2Result
    
    def _clear_memory(self):
        '''
        Clears memory of current object
        '''
        self.job_ids = []
        self.jobId2DocName = {}
        self.jobId2ProcessType = {}
        self.jobId2TextractFunc = {}
        self.jobId2ResponseList = {}

    @property
    def textract(self):
        return self._textract    


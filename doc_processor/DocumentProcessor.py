import time
import sys

import boto3
import concurrent.futures

import tempfile
from io import BytesIO
from pdf2image import convert_from_bytes



class ProcessType:
    '''
    Enum type class for textract process type
    '''
    DETECTION = "DETECTION"
    ANALYSIS = "ANALYSIS"



class SingleDocumentProcessor:
    '''
    This class process a single s3 pdf document by converting pages into image then extract information from it
    This is a iterator class
    '''
    textract = boto3.client("textract")
    pageNum2BytesArr = {} # dict mapping page number to corresponding bytes array

    def __init__(self, s3_obj, process_type):
        if process_type in [ProcessType.DETECTION, ProcessType.ANALYSIS]:
            self.process_type = process_type
        else:
            raise Exception(
                f"Invalid Process Type: {process_type}\nUse only: {ProcessType.DETECTION}, {ProcessType.ANALYSIS}")

        print(f"Starting Processing Document: {s3_obj.key}")
        with tempfile.TemporaryDirectory() as temp_dir:
            imgs = convert_from_bytes(s3_obj.get()["Body"].read(), thread_count=100,
                                      output_folder=temp_dir, fmt="png", grayscale=True)
            page_nums = list(range(1, len(imgs)+1))
            with concurrent.futures.ThreadPoolExecutor() as executor:
                executor.map(self.image_to_bytes, imgs, page_nums)

    def __iter__(self):
        '''
        returns bytes array of next page of pdf
        '''
        page_nums = list(range(1, len(self.pageNum2BytesArr)+1))
        for page_num in page_nums:
            yield self.pageNum2BytesArr[page_num]

    def image_to_bytes(self, img, page_num):
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

    def get_single_page_results(self, page_num):
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
        get detection results from all pages of pdf

        return:
        =================
        pageNum2Result: dict that maps page number to corresponding aws textract response
        '''
        pageNum2Result = {}
        max_sim_calls = 20 # max same time call allowed for aws textract
        page_nums = list(self.pageNum2BytesArr.keys())
        cur_page_nums_slice = page_nums[:max_sim_calls]
        cur_right_index = max_sim_calls
        while len(cur_page_nums_slice):
            with concurrent.futures.ThreadPoolExecutor() as executor:
                results = executor.map(self.get_single_page_results, cur_page_nums_slice)
            for res in results:
                pageNum2Result[res[0]] = res[1]
            cur_page_nums_slice = page_nums[cur_right_index : cur_right_index+max_sim_calls]
            cur_right_index += max_sim_calls
        '''
        with concurrent.futures.ThreadPoolExecutor() as executor:
            results = executor.map(self.get_single_page_results, self.pageNum2BytesArr.keys())

        pageNum2Result = {res[0] : res[1] for res in results} # mapping page number to textract results
        '''
        self.clear_memory()
        return pageNum2Result

    def clear_memory(self):
        '''
        free the memory of current object
        '''
        self.pageNum2BytesArr = {}




class BatchDocumentProcessor:
    '''
    This class able to process multiple s3 documents using multithreads
    '''

    textract = boto3.client("textract")
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


    def check_job_status(self, job_id):
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


    def get_single_doc_results(self, job_id, status):
        '''
        Extract responses from a finished job

        Parameters:
        =================
        job_id: job_id of the textract job to get results

        status: status of the response from check_job_status function

        Return:
        =================
        job_id: job_id of the job that finished

        res_list: list of the json response that is extracted
        '''
        s = time.time()
        job_doc_name = self.jobId2DocName[job_id]
        if status == "SUCCEEDED":
            print(f"\nGetting Results For Job: {job_doc_name}")
            res_list = []
            response = self.jobId2TextractFunc[job_id](JobId=job_id)
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
            results = executor.map(self.check_job_status, self.job_ids)

        job_id_list = []
        status_list = []
        for res in results:
            job_id_list.append(res[0])
            status_list.append(res[1])
        # get results using multithreading
        with concurrent.futures.ThreadPoolExecutor() as executor:
            # reuslts is list of tuples (job_id, res_list)
            # res_list contains multiple response for job_id
            results = executor.map(self.get_single_doc_results, job_id_list, status_list)

        docName2Result = {self.jobId2DocName[result[0]] : result[1] for result in results}
        print("All Done")
        self.clear_memory()

        return docName2Result
    
    def clear_memory(self):
        '''
        Clears memory of current object
        '''
        self.job_ids = []
        self.jobId2DocName = {}
        self.jobId2ProcessType = {}
        self.jobId2TextractFunc = {}
        self.jobId2ResponseList = {}

    


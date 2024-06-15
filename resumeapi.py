from fastapi import FastAPI, HTTPException, UploadFile, File
from typing import List
import motor.motor_asyncio
from bson import Binary, ObjectId
from fastapi.responses import JSONResponse, FileResponse, StreamingResponse
import PyPDF2
import re
from io import BytesIO
import base64
import tempfile
import os
import logging

app = FastAPI()


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# MongoDB settings
MONGO_DETAILS = "mongodb+srv://sangaransiva91:tAcmAULwAfWZcKuo@resumedata.vs8vidt.mongodb.net/?retryWrites=true&w=majority&appName=resumedata"
client = motor.motor_asyncio.AsyncIOMotorClient(
    MONGO_DETAILS,
    tls=True,
    tlsAllowInvalidCertificates=True  # Disables SSL certificate verification
)
database = client.get_database("pdf_db")
collection = database.get_collection("pdf_files")

def extract_emails_from_pdf(file: BytesIO) -> List[str]:
    emails = set()
    reader = PyPDF2.PdfReader(file)
    for page in reader.pages:
        text = page.extract_text()
        found_emails = re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text)
        emails.update(found_emails)
    return list(emails)

@app.post("/upload/")
async def upload_pdf(file: UploadFile = File(...)):
    try:
        # Read the PDF file content
        pdf_content = await file.read()

        emails = extract_emails_from_pdf(BytesIO(pdf_content))

        if not emails:
            raise HTTPException(status_code=400, detail="No emails found in the PDF file")

        document = {
            "filename": file.filename,
            "file": Binary(pdf_content),
            "emails": emails
        }
        result = await collection.insert_one(document)
        
        return {"pdf_id": str(result.inserted_id), "emails": emails}
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@app.get("/pdf")
async def get_all_pdfs():
    try:
        documents = await collection.find().to_list(length=None)
        for document in documents:
            document["_id"] = str(document["_id"])
            document["file"] = str(document["file"])  # Convert Binary data to string for JSON serialization
        return {"pdfs": documents}
    except Exception as e:
        logger.exception("An unexpected error occurred while retrieving all PDFs")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@app.get("/pdf/{pdf_id}")
async def get_pdf(pdf_id: str):
    try:
        document = await collection.find_one({"_id": ObjectId(pdf_id)})
        if document is None:
            raise HTTPException(status_code=404, detail="PDF not found")

        # Convert the binary data to PDF
        pdf_content = document["file"]
        pdf_filename = document["filename"]

        # a temporary file path to save the PDF
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
        temp_file.write(pdf_content)
        temp_file_path = temp_file.name
        temp_file.close()

        def iterfile():
            with open(temp_file_path, "rb") as f:
                yield from f
            os.remove(temp_file_path)
 
        return StreamingResponse(iterfile(), media_type="application/pdf", headers={"Content-Disposition": f"attachment; filename={pdf_filename}"})
    except HTTPException as e:
        logger.error(f"HTTP exception occurred: {e.detail}")
        raise e
    except Exception as e:
        logger.exception("An unexpected error occurred during PDF retrieval")
        raise HTTPException(status_code=500, detail="Internal Server Error")

import streamlit as st
from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import DocumentAnalysisFeature, AnalyzeResult
import os
import json

# Azure credentials
endpoint = "https://qrdecoder.cognitiveservices.azure.com/"
api_key = "dfeb2f070d6b49cba47e902f70dd148b"
model_id = "FormRecognizer"

form_recognizer_client = DocumentAnalysisClient(endpoint=endpoint, credential=AzureKeyCredential(api_key))
document_intelligence_client = DocumentIntelligenceClient(endpoint=endpoint, credential=AzureKeyCredential(api_key))

def analyze_document(file_path=None, document_url=None):
    if file_path:
        with open(file_path, "rb") as document:
            form_recognizer_poller = form_recognizer_client.begin_analyze_document(model_id=model_id, document=document)
    elif document_url:
        form_recognizer_poller = form_recognizer_client.begin_analyze_document_from_url(model_id=model_id, document_url=document_url)
    else:
        raise ValueError("Either file_path or document_url must be provided")
    
    form_recognizer_result = form_recognizer_poller.result()

    documents_json = []
    for idx, document in enumerate(form_recognizer_result.documents):
        doc_fields = {}
        for field_name, field in document.fields.items():
            doc_fields[field_name] = {
                "value": field.value,
                "confidence": field.confidence
            }
        documents_json.append(doc_fields)

    return documents_json

def analyze_barcodes(file_path):
    path_to_sample_documents = os.path.abspath(file_path)

    with open(path_to_sample_documents, "rb") as f:
        poller = document_intelligence_client.begin_analyze_document(
            "prebuilt-layout",
            analyze_request=f,
            features=[DocumentAnalysisFeature.BARCODES],
            content_type="application/pdf"
        )
    result: AnalyzeResult = poller.result()

    barcodes_json = []
    for page in result.pages:
        page_barcodes = {
            "page_number": page.page_number,
            "barcodes": []
        }
        if page.barcodes:
            for barcode in page.barcodes:
                page_barcodes["barcodes"].append({
                    "value": barcode.value,
                    "kind": barcode.kind,
                    "confidence": barcode.confidence
                })
        barcodes_json.append(page_barcodes)

    return barcodes_json

def analyze_document_with_barcodes(file_path=None, document_url=None):
    result_json = {}
    
    if file_path:
        result_json["document_fields"] = analyze_document(file_path=file_path)
        result_json["barcodes"] = analyze_barcodes(file_path)
    elif document_url:
        result_json["document_fields"] = analyze_document(document_url=document_url)
    else:
        raise ValueError("Either file_path or document_url must be provided")
    
    return json.dumps(result_json, indent=4)

# Streamlit UI
st.title("Document Analyzer with Barcodes")

# Upload file
uploaded_file = st.file_uploader("Choose a PDF file", type="pdf")

# Or provide a URL
document_url = st.text_input("Or provide a document URL")

# Button to trigger analysis
if st.button("Analyze"):
    if uploaded_file:
        file_path = os.path.join("tempDir", uploaded_file.name)
        os.makedirs("tempDir", exist_ok=True)
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        json_output = analyze_document_with_barcodes(file_path=file_path)
        os.remove(file_path)  # Clean up the temporary file
    elif document_url:
        json_output = analyze_document_with_barcodes(document_url=document_url)
    else:
        st.error("Please upload a file or provide a URL.")
        json_output = None
    
    if json_output:
        st.json(json_output)

import streamlit as st
import os
from langchain_groq import ChatGroq
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate
from langchain.chains import create_retrieval_chain
from langchain_community.vectorstores import FAISS
from langchain_community.document_loaders import PyPDFLoader
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from dotenv import load_dotenv
import time

# Load environment variables
load_dotenv()

# Load GROQ and Google API keys
groq_api_key = os.getenv('GROQ_API_KEY')
os.environ["GOOGLE_API_KEY"] = os.getenv("GOOGLE_API_KEY")

# Streamlit app title
st.title("Gemma Model Document Q&A")

# Initialize the language model
llm = ChatGroq(groq_api_key=groq_api_key, model_name="Gemma-7b-it")

# Define the prompt template
prompt = ChatPromptTemplate.from_template("""
Answer the questions based on the provided context only.
Please provide the most accurate response based on the question.
<context>
{context}
<context>
Questions: {input}
""")

# Function to process user-uploaded documents and create vector embeddings
def vector_embedding(uploaded_files):
    if "vectors" not in st.session_state:
        st.session_state.embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
        docs = []

        # Load uploaded documents
        for uploaded_file in uploaded_files:
            with open(uploaded_file.name, "wb") as f:
                f.write(uploaded_file.getbuffer())  # Save the uploaded file temporarily
            loader = PyPDFLoader(uploaded_file.name)  # Load the uploaded PDF
            docs.extend(loader.load())

        # Split the documents into chunks
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        final_documents = text_splitter.split_documents(docs)

        # Create vector embeddings
        st.session_state.vectors = FAISS.from_documents(final_documents, st.session_state.embeddings)
        st.session_state.final_documents = final_documents  # Store the documents for retrieval

# User file uploader for PDF documents
uploaded_files = st.file_uploader("Upload your documents (PDF only)", type=["pdf"], accept_multiple_files=True)

# Button to process and embed the uploaded documents
if st.button("Process Documents"):
    if uploaded_files:
        vector_embedding(uploaded_files)
        st.success("Vector Store DB is ready.")
    else:
        st.warning("Please upload at least one PDF document.")

# Text input for the user's query
prompt1 = st.text_input("Enter your question from the documents")

# Process the user's query
if prompt1:
    if "vectors" in st.session_state:
        document_chain = create_stuff_documents_chain(llm, prompt)
        retriever = st.session_state.vectors.as_retriever()
        retrieval_chain = create_retrieval_chain(retriever, document_chain)
        
        start = time.process_time()
        response = retrieval_chain.invoke({'input': prompt1})
        st.write("Response time:", time.process_time() - start)
        st.write(response['answer'])

        # Display relevant chunks with a Streamlit expander
        with st.expander("Document Similarity Search"):
            for i, doc in enumerate(response["context"]):
                st.write(doc.page_content)
                st.write("--------------------------------")
    else:
        st.warning("Please process and embed the documents first.")

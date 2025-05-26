import os
import json
from pinecone import Pinecone, ServerlessSpec
import google.generativeai as genai
from dotenv import load_dotenv
import time
import hashlib
import re
import PyPDF2
import docx
from io import BytesIO
import streamlit as st

# Load environment variables
load_dotenv()

class JobUploader:
    def __init__(self):
        """Initialize Pinecone and Google AI connections"""
        # Initialize Pinecone
        self.pc = Pinecone(api_key=os.getenv('PINECONE_API_KEY'))
        self.index_name = os.getenv('PINECONE_INDEX_NAME', 'job-descriptions')
        
        # Initialize Google AI
        genai.configure(api_key=os.getenv('GOOGLE_API_KEY'))
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        
        # Create or connect to index
        self.setup_index()
    
    def setup_index(self):
        """Setup Pinecone index"""
        try:
            # Check if index exists
            existing_indexes = self.pc.list_indexes().names()
            
            if self.index_name not in existing_indexes:
                print(f"Creating index: {self.index_name}")
                self.pc.create_index(
                    name=self.index_name,
                    dimension=1536,  # Standard dimension for text embeddings
                    metric='cosine',
                    spec=ServerlessSpec(
                        cloud='aws',
                        region='us-east-1'  # Change as needed
                    )
                )
                # Wait for index to be ready
                print("Waiting for index to be ready...")
                time.sleep(60)  # Increased wait time
            
            # Connect to index
            self.index = self.pc.Index(self.index_name)
            print(f"Connected to index: {self.index_name}")
            
        except Exception as e:
            print(f"Error setting up index: {str(e)}")
            raise e
    
    def generate_embedding(self, text):
        """Generate embedding for text using Google AI"""
        try:
            # Use Gemini to generate embeddings
            # Note: This is a simplified approach - you might want to use a dedicated embedding model
            response = genai.embed_content(
                model="models/embedding-001",
                content=text,
                task_type="retrieval_document"
            )
            return response['embedding']
        except Exception as e:
            print(f"Error generating embedding: {str(e)}")
            # Fallback: generate a simple hash-based vector (not recommended for production)
            return self.generate_fallback_embedding(text)
    
    def generate_fallback_embedding(self, text, dimension=1536):
        """Generate a fallback embedding using hash (for development only)"""
        # Create a hash of the text
        text_hash = hashlib.md5(text.encode()).hexdigest()
        
        # Convert hash to numbers and normalize
        hash_numbers = [ord(c) for c in text_hash]
        
        # Extend to required dimension
        embedding = []
        for i in range(dimension):
            embedding.append(hash_numbers[i % len(hash_numbers)] / 255.0)
        
        return embedding
    
    def create_job_text(self, job_data):
        """Create searchable text from job data"""
        text_parts = []
        
        if job_data.get('job_title'):
            text_parts.append(f"Job Title: {job_data['job_title']}")
        
        if job_data.get('company'):
            text_parts.append(f"Company: {job_data['company']}")
        
        if job_data.get('location'):
            text_parts.append(f"Location: {job_data['location']}")
        
        if job_data.get('description'):
            text_parts.append(f"Description: {job_data['description']}")
        
        if job_data.get('requirements'):
            text_parts.append(f"Requirements: {job_data['requirements']}")
        
        if job_data.get('salary'):
            text_parts.append(f"Salary: {job_data['salary']}")
        
        if job_data.get('employment_type'):
            text_parts.append(f"Employment Type: {job_data['employment_type']}")
        
        if job_data.get('experience_level'):
            text_parts.append(f"Experience Level: {job_data['experience_level']}")
        
        if job_data.get('benefits'):
            text_parts.append(f"Benefits: {job_data['benefits']}")
        
        return " | ".join(text_parts)
    
    def upload_job_to_pinecone(self, job_data):
        """Upload a single job to Pinecone"""
        try:
            # Create job text for embedding
            job_text = self.create_job_text(job_data)
            
            # Generate embedding
            embedding = self.generate_embedding(job_text)
            
            # Create unique ID for the job
            job_id = hashlib.md5(
                f"{job_data.get('company', '')}-{job_data.get('job_title', '')}-{time.time()}".encode()
            ).hexdigest()
            
            # Prepare metadata
            metadata = {
                'job_title': job_data.get('job_title', ''),
                'company': job_data.get('company', ''),
                'location': job_data.get('location', ''),
                'description': job_data.get('description', '')[:1000],  # Limit description length
                'requirements': job_data.get('requirements', '')[:500],  # Limit requirements length
                'salary': job_data.get('salary', ''),
                'employment_type': job_data.get('employment_type', ''),
                'experience_level': job_data.get('experience_level', ''),
                'benefits': job_data.get('benefits', '')[:500],  # Limit benefits length
                'full_text': job_text[:2000]  # Store searchable text (limited)
            }
            
            # Upload to Pinecone
            self.index.upsert(
                vectors=[{
                    'id': job_id,
                    'values': embedding,
                    'metadata': metadata
                }]
            )
            
            print(f"Successfully uploaded job: {job_data.get('job_title', 'Unknown')}")
            return True
            
        except Exception as e:
            print(f"Error uploading job: {str(e)}")
            return False
    
    def get_index_stats(self):
        """Get Pinecone index statistics"""
        try:
            stats = self.index.describe_index_stats()
            return stats
        except Exception as e:
            print(f"Error getting index stats: {str(e)}")
            return {'error': str(e)}
    
    def search_jobs(self, query, top_k=10):
        """Search for jobs using query"""
        try:
            # Generate embedding for query
            query_embedding = self.generate_embedding(query)
            
            # Search in Pinecone
            results = self.index.query(
                vector=query_embedding,
                top_k=top_k,
                include_metadata=True
            )
            
            return results.matches
            
        except Exception as e:
            print(f"Error searching jobs: {str(e)}")
            return []
    
    def delete_all_jobs(self):
        """Delete all jobs from the index (use with caution!)"""
        try:
            # Get all vector IDs
            stats = self.index.describe_index_stats()
            
            if stats.total_vector_count > 0:
                # Delete all vectors
                self.index.delete(delete_all=True)
                print("All jobs deleted from index")
                return True
            else:
                print("No jobs to delete")
                return True
                
        except Exception as e:
            print(f"Error deleting jobs: {str(e)}")
            return False


class ResumeAnalyzer:
    def __init__(self):
        """Initialize ResumeAnalyzer with Pinecone and Google AI"""
        # Initialize Pinecone
        self.pc = Pinecone(api_key=os.getenv('PINECONE_API_KEY'))
        self.index_name = os.getenv('PINECONE_INDEX_NAME', 'job-descriptions')
        
        # Initialize Google AI
        genai.configure(api_key=os.getenv('GOOGLE_API_KEY'))
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        
        # Connect to existing index
        self.setup_index()
    
    def setup_index(self):
        """Connect to existing Pinecone index"""
        try:
            # Check if index exists
            existing_indexes = self.pc.list_indexes().names()
            
            if self.index_name not in existing_indexes:
                raise Exception(f"Index '{self.index_name}' does not exist. Please create it first using JobUploader.")
            
            # Connect to index
            self.index = self.pc.Index(self.index_name)
            print(f"Connected to index: {self.index_name}")
            
        except Exception as e:
            print(f"Error connecting to index: {str(e)}")
            raise e
    
    def extract_text_from_file(self, uploaded_file):
        """Extract text from uploaded file"""
        try:
            file_extension = uploaded_file.name.split('.')[-1].lower()
            
            if file_extension == 'pdf':
                return self.extract_text_from_pdf(uploaded_file)
            elif file_extension == 'docx':
                return self.extract_text_from_docx(uploaded_file)
            elif file_extension == 'txt':
                return self.extract_text_from_txt(uploaded_file)
            else:
                raise Exception(f"Unsupported file format: {file_extension}")
                
        except Exception as e:
            raise Exception(f"Error extracting text: {str(e)}")
    
    def extract_text_from_pdf(self, uploaded_file):
        """Extract text from PDF file"""
        try:
            pdf_reader = PyPDF2.PdfReader(BytesIO(uploaded_file.read()))
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
            return text.strip()
        except Exception as e:
            raise Exception(f"Error reading PDF: {str(e)}")
    
    def extract_text_from_docx(self, uploaded_file):
        """Extract text from DOCX file"""
        try:
            doc = docx.Document(BytesIO(uploaded_file.read()))
            text = ""
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
            return text.strip()
        except Exception as e:
            raise Exception(f"Error reading DOCX: {str(e)}")
    
    def extract_text_from_txt(self, uploaded_file):
        """Extract text from TXT file"""
        try:
            return uploaded_file.read().decode('utf-8')
        except Exception as e:
            raise Exception(f"Error reading TXT: {str(e)}")
    
    def parse_resume(self, resume_text):
        """Parse resume to extract key information"""
        try:
            # Extract email
            email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            emails = re.findall(email_pattern, resume_text)
            email = emails[0] if emails else None
            
            # Extract phone number
            phone_pattern = r'(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}'
            phones = re.findall(phone_pattern, resume_text)
            phone = ''.join(phones[0]) if phones else None
            
            # Extract name (simple approach - first line or first few words)
            lines = resume_text.split('\n')
            name = None
            for line in lines:
                line = line.strip()
                if line and len(line.split()) <= 4 and not any(char.isdigit() for char in line):
                    if '@' not in line and not any(keyword in line.lower() for keyword in ['resume', 'cv', 'email', 'phone']):
                        name = line
                        break
            
            # Extract skills using AI
            skills = self.extract_skills_with_ai(resume_text)
            
            return {
                'name': name,
                'email': email,
                'phone': phone,
                'skills': skills,
                'full_text': resume_text
            }
            
        except Exception as e:
            print(f"Error parsing resume: {str(e)}")
            return {
                'name': None,
                'email': None,
                'phone': None,
                'skills': [],
                'full_text': resume_text
            }
    
    def extract_skills_with_ai(self, resume_text):
        """Extract skills from resume using AI"""
        try:
            prompt = f"""
            Extract the key technical and professional skills from this resume text. 
            Return only a comma-separated list of skills, no explanations.
            Focus on technical skills, programming languages, tools, certifications, and relevant professional skills.
            
            Resume text:
            {resume_text[:2000]}  # Limit text length
            """
            
            response = self.model.generate_content(prompt)
            skills_text = response.text.strip()
            
            # Parse skills from response
            skills = [skill.strip() for skill in skills_text.split(',') if skill.strip()]
            return skills[:10]  # Limit to top 10 skills
            
        except Exception as e:
            print(f"Error extracting skills with AI: {str(e)}")
            return []
    
    def generate_embedding(self, text):
        """Generate embedding for text using Google AI"""
        try:
            response = genai.embed_content(
                model="models/embedding-001",
                content=text,
                task_type="retrieval_query"
            )
            return response['embedding']
        except Exception as e:
            print(f"Error generating embedding: {str(e)}")
            # Fallback: generate a simple hash-based vector
            return self.generate_fallback_embedding(text)
    
    def generate_fallback_embedding(self, text, dimension=1536):
        """Generate a fallback embedding using hash (for development only)"""
        text_hash = hashlib.md5(text.encode()).hexdigest()
        hash_numbers = [ord(c) for c in text_hash]
        embedding = []
        for i in range(dimension):
            embedding.append(hash_numbers[i % len(hash_numbers)] / 255.0)
        return embedding
    
    def search_matching_jobs(self, resume_text, top_k=5):
        """Search for matching jobs based on resume"""
        try:
            # Generate embedding for resume
            resume_embedding = self.generate_embedding(resume_text)
            
            # Search in Pinecone
            results = self.index.query(
                vector=resume_embedding,
                top_k=top_k,
                include_metadata=True
            )
            
            # Format results
            job_matches = []
            for match in results.matches:
                job_data = {
                    'job_title': match.metadata.get('job_title', 'Unknown'),
                    'company': match.metadata.get('company', 'Unknown'),
                    'location': match.metadata.get('location', 'Unknown'),
                    'description': match.metadata.get('description', 'No description available'),
                    'requirements': match.metadata.get('requirements', ''),
                    'salary': match.metadata.get('salary', 'Not specified'),
                    'employment_type': match.metadata.get('employment_type', 'Not specified'),
                    'experience_level': match.metadata.get('experience_level', 'Not specified'),
                    'score': match.score
                }
                job_matches.append(job_data)
            
            return job_matches
            
        except Exception as e:
            print(f"Error searching for matching jobs: {str(e)}")
            return []
    
    def generate_analysis(self, resume_text, job_matches):
        """Generate comprehensive analysis using AI"""
        try:
            # Prepare job matches text
            jobs_text = ""
            for i, job in enumerate(job_matches[:3], 1):  # Top 3 jobs
                jobs_text += f"""
                Job {i}: {job['job_title']} at {job['company']}
                Location: {job['location']}
                Match Score: {job['score']:.2f}
                Description: {job['description'][:300]}...
                Requirements: {job['requirements'][:200]}...
                
                """
            
            prompt = f"""
            As an expert career counselor and resume analyst, provide a comprehensive analysis of this resume and job matching results.
            
            ## RESUME TEXT:
            {resume_text[:3000]}
            
            ## TOP MATCHING JOBS:
            {jobs_text}
            
            Please provide a detailed analysis covering these sections:
            
            ## Resume Strengths
            Identify and explain the key strengths in this resume.
            
            ## Areas for Improvement
            Suggest specific improvements for the resume.
            
            ## Job Match Analysis
            Analyze why these jobs are good matches and what might be missing.
            
            ## Skill Gap Analysis
            Identify skills that are in demand but missing from the resume.
            
            ## Career Recommendations
            Provide actionable career advice and next steps.
            
            ## Resume Optimization Tips
            Suggest specific ways to optimize the resume for better job matches.
            
            Keep the analysis practical, specific, and actionable. Use bullet points where appropriate.
            """
            
            response = self.model.generate_content(prompt)
            return response.text
            
        except Exception as e:
            print(f"Error generating analysis: {str(e)}")
            return "Error generating analysis. Please try again."
import streamlit as st
import pandas as pd
import json
import os
from dotenv import load_dotenv
from utils import JobUploader

# Load environment variables
load_dotenv()

# Page configuration
st.set_page_config(
    page_title="Job Description Uploader",
    page_icon="💼",
    layout="wide"
)

# Initialize session state
if 'uploader' not in st.session_state:
    try:
        with st.spinner("Initializing connections..."):
            st.session_state.uploader = JobUploader()
        st.session_state.connection_status = "✅ Connected"
    except Exception as e:
        st.session_state.uploader = None
        st.session_state.connection_status = f"❌ Connection Error: {str(e)}"

def main():
    st.title("💼 Job Description Uploader")
    st.markdown("Upload job descriptions to Pinecone vector database")
    
    # Connection status
    if st.session_state.connection_status.startswith("✅"):
        st.success(st.session_state.connection_status)
    else:
        st.error(st.session_state.connection_status)
        st.stop()
    
    # Sidebar for method selection
    st.sidebar.title("Upload Method")
    upload_method = st.sidebar.radio(
        "Choose upload method:",
        ["Manual Entry", "File Upload", "Database Stats", "Connection Test"]
    )
    
    if upload_method == "Manual Entry":
        manual_entry_section()
    elif upload_method == "File Upload":
        file_upload_section()
    elif upload_method == "Database Stats":
        database_stats_section()
    else:
        connection_test_section()

def manual_entry_section():
    st.header("📝 Manual Job Entry")
    
    with st.form("manual_job_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            job_title = st.text_input("Job Title *", placeholder="e.g., Software Engineer")
            company = st.text_input("Company *", placeholder="e.g., Tech Corp")
            location = st.text_input("Location *", placeholder="e.g., New York, NY")
        
        with col2:
            salary = st.text_input("Salary (Optional)", placeholder="e.g., $80,000 - $120,000")
            employment_type = st.selectbox(
                "Employment Type",
                ["Full-time", "Part-time", "Contract", "Internship", "Remote"]
            )
            experience_level = st.selectbox(
                "Experience Level",
                ["Entry Level", "Mid Level", "Senior Level", "Executive"]
            )
        
        description = st.text_area(
            "Job Description *",
            height=200,
            placeholder="Enter detailed job description..."
        )
        
        requirements = st.text_area(
            "Requirements",
            height=150,
            placeholder="Enter job requirements, skills, qualifications..."
        )
        
        benefits = st.text_area(
            "Benefits (Optional)",
            height=100,
            placeholder="Enter benefits and perks..."
        )
        
        submitted = st.form_submit_button("🚀 Upload Job", use_container_width=True)
        
        if submitted:
            if not all([job_title, company, location, description]):
                st.error("Please fill in all required fields (marked with *)")
            else:
                job_data = {
                    'job_title': job_title,
                    'company': company,
                    'location': location,
                    'description': description,
                    'requirements': requirements,
                    'salary': salary,
                    'employment_type': employment_type,
                    'experience_level': experience_level,
                    'benefits': benefits
                }
                
                try:
                    with st.spinner("Uploading job..."):
                        success = st.session_state.uploader.upload_job_to_pinecone(job_data)
                    
                    if success:
                        st.success("✅ Job uploaded successfully!")
                        st.balloons()
                        # Clear form by rerunning
                        st.rerun()
                    else:
                        st.error("❌ Failed to upload job")
                except Exception as e:
                    st.error(f"❌ Upload failed: {str(e)}")

def file_upload_section():
    st.header("📂 File Upload")
    st.markdown("Upload multiple jobs from CSV or JSON files")
    
    # File format information
    with st.expander("📋 File Format Requirements"):
        st.markdown("""
        **Required Fields:**
        - `job_title`: Job title
        - `company`: Company name
        - `location`: Job location
        - `description`: Job description
        
        **Optional Fields:**
        - `requirements`: Job requirements
        - `salary`: Salary information
        - `employment_type`: Full-time, Part-time, etc.
        - `experience_level`: Entry, Mid, Senior, etc.
        - `benefits`: Benefits and perks
        """)
        
        # Sample data
        sample_data = {
            "job_title": ["Software Engineer", "Data Scientist"],
            "company": ["Tech Corp", "AI Solutions"],
            "location": ["New York, NY", "San Francisco, CA"],
            "description": [
                "Develop and maintain web applications using modern technologies.",
                "Analyze large datasets and build machine learning models."
            ],
            "requirements": [
                "3+ years Python experience, React, Node.js",
                "PhD in Statistics/CS, Python, R, SQL"
            ]
        }
        
        st.markdown("**Sample CSV format:**")
        st.dataframe(pd.DataFrame(sample_data))
    
    uploaded_file = st.file_uploader(
        "Choose a file",
        type=['csv', 'json'],
        help="Upload CSV or JSON file with job descriptions"
    )
    
    if uploaded_file is not None:
        try:
            # Preview file
            st.subheader("📊 File Preview")
            
            if uploaded_file.name.endswith('.csv'):
                df = pd.read_csv(uploaded_file)
                jobs_data = df.to_dict('records')
            else:  # JSON
                jobs_data = json.load(uploaded_file)
                df = pd.DataFrame(jobs_data)
            
            st.dataframe(df.head())
            st.info(f"Found {len(jobs_data)} jobs in the file")
            
            # Validate required fields
            required_fields = ['job_title', 'company', 'location', 'description']
            missing_fields = [field for field in required_fields if field not in df.columns]
            
            if missing_fields:
                st.error(f"❌ Missing required fields: {', '.join(missing_fields)}")
            else:
                col1, col2, col3 = st.columns([1, 2, 1])
                with col2:
                    if st.button("🚀 Upload All Jobs", use_container_width=True):
                        upload_jobs_from_data(jobs_data)
        
        except Exception as e:
            st.error(f"❌ Error reading file: {str(e)}")

def upload_jobs_from_data(jobs_data):
    """Upload jobs from processed data"""
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    uploaded_count = 0
    failed_count = 0
    failed_jobs = []
    
    for i, job in enumerate(jobs_data):
        progress = (i + 1) / len(jobs_data)
        progress_bar.progress(progress)
        status_text.text(f"Processing job {i + 1} of {len(jobs_data)}")
        
        try:
            success = st.session_state.uploader.upload_job_to_pinecone(job)
            if success:
                uploaded_count += 1
            else:
                failed_count += 1
                failed_jobs.append(f"Job {i + 1}: {job.get('job_title', 'Unknown')}")
        except Exception as e:
            failed_count += 1
            failed_jobs.append(f"Job {i + 1}: {job.get('job_title', 'Unknown')} - Error: {str(e)}")
    
    progress_bar.empty()
    status_text.empty()
    
    # Show results
    col1, col2 = st.columns(2)
    with col1:
        st.metric("✅ Successfully Uploaded", uploaded_count)
    with col2:
        st.metric("❌ Failed", failed_count)
    
    if uploaded_count > 0:
        st.success(f"🎉 Successfully uploaded {uploaded_count} jobs!")
        if uploaded_count == len(jobs_data):
            st.balloons()
    
    if failed_jobs:
        with st.expander(f"⚠️ Failed Jobs ({failed_count})"):
            for failed_job in failed_jobs:
                st.text(failed_job)

def database_stats_section():
    st.header("📊 Database Statistics")
    
    col1, col2 = st.columns([2, 1])
    with col2:
        if st.button("🔄 Refresh Stats", use_container_width=True):
            st.rerun()
    
    try:
        with st.spinner("Loading statistics..."):
            stats = st.session_state.uploader.get_index_stats()
        
        # Display metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "Total Vectors",
                stats.get('total_vector_count', 'N/A')
            )
        
        with col2:
            st.metric(
                "Namespaces",
                len(stats.get('namespaces', {}))
            )
        
        with col3:
            fullness = stats.get('index_fullness', 0)
            if isinstance(fullness, (int, float)):
                fullness_pct = f"{fullness:.2%}"
            else:
                fullness_pct = str(fullness)
            st.metric("Index Fullness", fullness_pct)
        
        with col4:
            st.metric(
                "Dimension",
                stats.get('dimension', 'N/A')
            )
        
        # Detailed stats
        st.subheader("📈 Detailed Statistics")
        
        if 'namespaces' in stats and stats['namespaces']:
            st.markdown("**Namespaces:**")
            for namespace, ns_stats in stats['namespaces'].items():
                st.markdown(f"- `{namespace}`: {ns_stats.get('vector_count', 0)} vectors")
        
        # Raw stats (expandable)
        with st.expander("🔍 Raw Statistics Data"):
            st.json(stats)
    
    except Exception as e:
        st.error(f"❌ Error retrieving stats: {str(e)}")

def connection_test_section():
    st.header("🔧 Connection Test")
    st.markdown("Test connections to all services")
    
    if st.button("🧪 Run Connection Test", type="primary"):
        if not st.session_state.uploader:
            st.error("❌ JobUploader not initialized")
            return
        
        with st.spinner("Testing connections..."):
            results = st.session_state.uploader.test_connection()
        
        st.subheader("Test Results")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if results['pinecone']:
                st.success("✅ Pinecone")
            else:
                st.error("❌ Pinecone")
        
        with col2:
            if results['google_ai']:
                st.success("✅ Google AI")
            else:
                st.error("❌ Google AI")
        
        with col3:
            if results['index']:
                st.success("✅ Index")
            else:
                st.error("❌ Index")
        
        if all(results.values()):
            st.success("🎉 All connections successful!")
        else:
            st.warning("⚠️ Some connections failed. Check your API keys and configuration.")
            
            with st.expander("🔍 Troubleshooting Tips"):
                st.markdown("""
                **Common Issues:**
                1. **Missing API Keys**: Check your `.env` file
                2. **Invalid API Keys**: Verify your Pinecone and Google AI keys
                3. **Index Creation**: First run might take time to create index
                4. **Network Issues**: Check internet connection
                
                **Required Environment Variables:**
                - `PINECONE_API_KEY`
                - `GOOGLE_API_KEY`
                - `PINECONE_INDEX_NAME` (optional, defaults to 'job-descriptions')
                """)

if __name__ == "__main__":
    main()
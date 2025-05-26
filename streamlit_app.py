import streamlit as st
import os
from dotenv import load_dotenv
from utils import ResumeAnalyzer
import time

# Load environment variables
load_dotenv()

# Page configuration
st.set_page_config(
    page_title="Resume Analyzer & Job Matcher",
    page_icon="📄",
    layout="wide"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        text-align: center;
        color: #1f77b4;
        font-size: 2.5rem;
        font-weight: bold;
        margin-bottom: 2rem;
    }
    .job-match-card {
        background-color: #000000;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f77b4;
        margin-bottom: 1rem;
        border: 1px solid #e9ecef;
    }
    .match-score {
        background-color: #28a745;
        color: white;
        padding: 0.2rem 0.5rem;
        border-radius: 0.3rem;
        font-weight: bold;
    }
    .skill-badge {
        display: inline-block;
        background-color: #007bff;
        color: white;
        padding: 0.3rem 0.8rem;
        margin: 0.2rem;
        border-radius: 1rem;
        font-size: 0.8rem;
        font-weight: 500;
    }
    .stTextArea textarea {
        height: 200px;
    }
</style>
""", unsafe_allow_html=True)

def initialize_analyzer():
    """Initialize the ResumeAnalyzer"""
    try:
        if 'analyzer' not in st.session_state:
            with st.spinner("Initializing AI services..."):
                st.session_state.analyzer = ResumeAnalyzer()
        return st.session_state.analyzer
    except Exception as e:
        st.error(f"Failed to initialize services: {str(e)}")
        st.error("Please check your API keys in the .env file")
        return None

def main():
    # Header
    st.markdown('<h1 class="main-header">📄 Resume Analyzer & Job Matcher</h1>', unsafe_allow_html=True)
    
    # Initialize analyzer
    analyzer = initialize_analyzer()
    if not analyzer:
        st.stop()
    
    # Main content
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.header("📤 Upload Resume")
        uploaded_file = st.file_uploader(
            "Choose your resume file",
            type=['pdf', 'docx', 'txt'],
            help="Upload your resume in PDF, DOCX, or TXT format"
        )
        
        # Add number of matches selector
        st.subheader("⚙️ Settings")
        num_matches = st.slider(
            "Number of job matches to find:",
            min_value=3,
            max_value=15,
            value=8,
            help="Select how many job matches you want to see"
        )
        
        if uploaded_file is not None:
            # File details
            st.success(f"✅ File uploaded: {uploaded_file.name}")
            st.info(f"File size: {uploaded_file.size} bytes")
            
            # Extract text button
            if st.button("🔍 Analyze Resume", type="primary"):
                with st.spinner("Extracting and analyzing resume..."):
                    try:
                        # Extract text from uploaded file
                        resume_text = analyzer.extract_text_from_file(uploaded_file)
                        
                        # Store in session state
                        st.session_state.resume_text = resume_text
                        st.session_state.resume_parsed = analyzer.parse_resume(resume_text)
                        
                        # Search for matching jobs
                        with st.spinner("Finding matching jobs..."):
                            job_matches = analyzer.search_matching_jobs(resume_text, top_k=num_matches)
                            st.session_state.job_matches = job_matches
                        
                        # Generate AI analysis
                        with st.spinner("Generating AI insights..."):
                            analysis = analyzer.generate_analysis(resume_text, job_matches)
                            st.session_state.analysis = analysis
                        
                        st.success("✅ Analysis complete!")
                        st.rerun()
                        
                    except Exception as e:
                        st.error(f"Error processing resume: {str(e)}")
    
    with col2:
        st.header("📋 Resume Analysis")
        
        # Show parsed resume info if available
        if 'resume_parsed' in st.session_state:
            resume_data = st.session_state.resume_parsed
            
            st.subheader("📝 Extracted Information")
            
            col2_1, col2_2 = st.columns(2)
            with col2_1:
                if resume_data.get('name'):
                    st.write(f"**Name:** {resume_data['name']}")
                if resume_data.get('email'):
                    st.write(f"**Email:** {resume_data['email']}")
            
            with col2_2:
                if resume_data.get('skills'):
                    st.write("**Skills Found:**")
                    # Create HTML for skill badges
                    skills_html = ""
                    for skill in resume_data['skills']:
                        skills_html += f'<span class="skill-badge">{skill}</span>'
                    st.markdown(skills_html, unsafe_allow_html=True)
            
            st.divider()
    
    # Job Matches Section
    if 'job_matches' in st.session_state:
        st.header("🎯 Top Job Matches")
        
        job_matches = st.session_state.job_matches
        
        if job_matches:
            for i, job in enumerate(job_matches, 1):
                with st.container():
                    # Safe access to job fields with defaults
                    job_title = job.get('job_title', 'N/A')
                    company = job.get('company', 'N/A')
                    location = job.get('location', 'N/A')
                    score = job.get('score', 0)
                    salary = job.get('salary', 'Not specified')
                    employment_type = job.get('employment_type', 'Not specified')
                    experience_level = job.get('experience_level', 'Not specified')
                    description = job.get('description', 'No description available')
                    
                    st.markdown(f"""
                    <div class="job-match-card">
                        <h4>#{i} {job_title} at {company}</h4>
                        <p><strong>Location:</strong> {location}</p>
                        <p><strong>Match Score:</strong> <span class="match-score">{score*100:.1f}%</span></p>
                        <p><strong>Salary:</strong> {salary}</p>
                        <p><strong>Employment Type:</strong> {employment_type}</p>
                        <p><strong>Experience Level:</strong> {experience_level}</p>
                        <p><strong>Description:</strong> {description[:200]}...</p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Add expander for full job details
                    with st.expander(f"View Full Details - {job_title}"):
                        st.write(f"**Company:** {company}")
                        st.write(f"**Location:** {location}")
                        st.write(f"**Salary:** {salary}")
                        st.write(f"**Employment Type:** {employment_type}")
                        st.write(f"**Experience Level:** {experience_level}")
                        st.write(f"**Match Score:** {score*100:.1f}%")
                        st.write("**Full Description:**")
                        st.write(description)
                        requirements = job.get('requirements', '')
                        if requirements:
                            st.write("**Requirements:**")
                            st.write(requirements)
        else:
            st.warning("No matching jobs found. The job database might be empty.")
            st.info("💡 Use the job uploader tool to add job descriptions to the database.")
    
    # AI Analysis Section
    if 'analysis' in st.session_state:
        st.header("🤖 AI-Powered Analysis")
        
        # Display the full analysis
        analysis_text = st.session_state.analysis
        
        # Split analysis into sections for better display
        sections = analysis_text.split('##')
        
        for section in sections[1:]:  # Skip first empty section
            if section.strip():
                lines = section.strip().split('\n')
                section_title = lines[0].strip()
                section_content = '\n'.join(lines[1:]).strip()
                
                if section_title:
                    st.subheader(f"## {section_title}")
                    st.markdown(section_content)
                    st.divider()
        
        # Download buttons
        st.header("📥 Download Results")
        
        col3_1, col3_2, col3_3 = st.columns(3)
        
        with col3_1:
            # Download full analysis
            st.download_button(
                label="📄 Download Full Analysis",
                data=analysis_text,
                file_name="resume_analysis.txt",
                mime="text/plain"
            )
        
        with col3_2:
            # Download job matches
            if 'job_matches' in st.session_state:
                job_matches_text = "TOP JOB MATCHES\n" + "="*50 + "\n\n"
                for i, job in enumerate(st.session_state.job_matches, 1):
                    job_title = job.get('job_title', 'N/A')
                    company = job.get('company', 'N/A')
                    location = job.get('location', 'N/A')
                    score = job.get('score', 0)
                    salary = job.get('salary', 'Not specified')
                    employment_type = job.get('employment_type', 'Not specified')
                    experience_level = job.get('experience_level', 'Not specified')
                    description = job.get('description', 'No description available')
                    requirements = job.get('requirements', '')
                    
                    job_matches_text += f"#{i} {job_title} at {company}\n"
                    job_matches_text += f"Location: {location}\n"
                    job_matches_text += f"Match Score: {score*100:.1f}%\n"
                    job_matches_text += f"Salary: {salary}\n"
                    job_matches_text += f"Employment Type: {employment_type}\n"
                    job_matches_text += f"Experience Level: {experience_level}\n"
                    job_matches_text += f"Description: {description}\n"
                    if requirements:
                        job_matches_text += f"Requirements: {requirements}\n"
                    job_matches_text += "-" * 50 + "\n\n"
                
                st.download_button(
                    label="🎯 Download Job Matches",
                    data=job_matches_text,
                    file_name="job_matches.txt",
                    mime="text/plain"
                )
        
        with col3_3:
            # Download resume data
            if 'resume_text' in st.session_state:
                st.download_button(
                    label="📝 Download Resume Text",
                    data=st.session_state.resume_text,
                    file_name="extracted_resume.txt",
                    mime="text/plain"
                )
    
    # Footer
    st.divider()
    st.markdown("""
    <div style="text-align: center; color: #666; margin-top: 2rem;">
        <p>🚀 Powered by Gemini AI & Pinecone Vector Database</p>
        <p>Made By Soham Soni</p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
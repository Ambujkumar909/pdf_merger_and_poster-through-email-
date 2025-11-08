import streamlit as st
import os
import fitz  # PyMuPDF for PDF merging
import zipfile
from io import BytesIO
from collections import defaultdict
import re
# --- CONFIGURATION ---
MAX_COMBINED_SIZE_MB = 15
MAX_FILE_COUNT = 10
# Set page configuration for a wider layout
st.set_page_config(layout="wide", page_title="PDF Batch Processor")

# Initialize Session State for Dynamic Sections
if 'num_sections' not in st.session_state:
    st.session_state.num_sections = 1
if 'all_files' not in st.session_state:
    st.session_state.all_files = []

# --- CORE PROCESSING FUNCTIONS ---


def merge_pdfs_in_memory(pdf_data_list):
    """Merges a list of PDF bytes data in memory using fitz (PyMuPDF)."""
    if not pdf_data_list:
        return None
    
    merged_document = fitz.open()
    try:
        for pdf_data in pdf_data_list:
            # Open PDF from bytes in memory
            doc = fitz.open(stream=pdf_data, filetype="pdf")
            merged_document.insert_pdf(doc)
            doc.close()
        
        # Save the merged document to a BytesIO object
        output_buffer = BytesIO(merged_document.write())
        return output_buffer
    except Exception as e:
        st.error(f"Error during PDF merge: {e}")
        return None
    finally:
        if 'merged_document' in locals():
            merged_document.close()

# --- UI MANAGEMENT FUNCTIONS ---


def add_section():
    """Increments the number of merge sections."""
    st.session_state.num_sections += 1


def remove_section(index):
    """Removes a merge section by index."""
    if st.session_state.num_sections > 1:
        # Shift data from higher indices down
        for i in range(index, st.session_state.num_sections - 1):
            st.session_state[f'po_{i}'] = st.session_state.get(f'po_{i+1}', "")
            st.session_state[f'loc_{i}'] = st.session_state.get(f'loc_{i+1}', "")
            st.session_state[f'files_{i}'] = st.session_state.get(f'files_{i+1}', [])
        
        # Delete the last section's state
        del st.session_state[f'po_{st.session_state.num_sections - 1}']
        del st.session_state[f'loc_{st.session_state.num_sections - 1}']
        del st.session_state[f'files_{st.session_state.num_sections - 1}']

        st.session_state.num_sections -= 1


def process_all_merges():
    """
    Executes all merge jobs, creates the final ZIP file, and prepares the download link.
    """
    
    st.session_state.merged_files_data = {}
    total_locations = []
    
    # Check for empty sections and merge files
    for i in range(st.session_state.num_sections):
        po = st.session_state.get(f'po_{i}', '').strip()
        location = st.session_state.get(f'loc_{i}', '').strip()
        files = st.session_state.get(f'files_{i}', [])
        
        if not po or not location:
            st.error(f"Section {i+1} is missing a PO or Location. Please fill out both fields.")
            return
            
        if not files:
            st.warning(f"Section {i+1} has no files selected. Skipping merge for this section.")
            continue
            
        # 1. Prepare Data for Merging
        pdf_data_list = [f.getvalue() for f in files]
        
        # 2. Execute Merge
        merged_buffer = merge_pdfs_in_memory(pdf_data_list)
        
        if merged_buffer:
            # 3. Define Filename
            safe_po = re.sub(r'[^a-zA-Z0-9-]', '', po)
            safe_loc = re.sub(r'[^a-zA-Z0-9-]', '', location)
            output_filename = f"{safe_po}-{safe_loc}.pdf"
            
            # Store merged file data
            st.session_state.merged_files_data[output_filename] = merged_buffer.getvalue()
            total_locations.append(safe_loc)

    if not st.session_state.merged_files_data:
        st.error("No valid merge jobs were processed. Please check input fields and file selections.")
        return

    # 4. Create ZIP Archive
    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        for filename, data in st.session_state.merged_files_data.items():
            zf.writestr(filename, data)

    # 5. Define ZIP Filename
    unique_locations = sorted(list(set(total_locations)))
    zip_filename = "-".join(unique_locations) + "_Merged_Batch.zip"
    
    # Store final zip data in session state for download button
    st.session_state.final_zip_data = zip_buffer.getvalue()
    st.session_state.final_zip_filename = zip_filename
    st.success(f"Successfully processed {len(st.session_state.merged_files_data)} merge jobs!")

# --- STREAMLIT UI ---


st.title("📄 PDF Batch Processor & Zipper")
st.markdown("Define multiple merge jobs below. Each job creates one PDF named `PO-Location.pdf` and all are collected into a single ZIP file.")
st.markdown("---")

# Main container for dynamic sections
sections_container = st.container()

with sections_container:
    # Use columns for layout control and Add/Remove buttons
    cols = st.columns([1, 1, 1, 1])
    with cols[0]:
        st.button("➕ Add More Merge Jobs", on_click=add_section, use_container_width=True, type="primary")

    # Dynamic Section Rendering Loop
    for i in range(st.session_state.num_sections):
        st.markdown(f"### Job #{i+1}")
        
        # Horizontal layout for inputs
        col1, col2, col3 = st.columns([2, 2, 1])
        
        with col1:
            st.text_input(
                "Purchase Order (PO)",
                key=f'po_{i}',
                placeholder="e.g., ORD12345",
                help="Used as the first part of the merged PDF filename."
            )
        
        with col2:
            st.text_input(
                "Location",
                key=f'loc_{i}',
                placeholder="e.g., NewYork-BldgA",
                help="Used as the second part of the merged PDF filename."
            )

        with col3:
            # Add a vertical space to align the remove button with inputs
            st.markdown("<div style='height: 2.5rem;'></div>", unsafe_allow_html=True) 
            if st.session_state.num_sections > 1:
                st.button("Remove", key=f'remove_{i}', on_click=remove_section, args=(i,), use_container_width=True)

        # File Uploader
        st.file_uploader(
            "Select PDFs to Merge for this Job",
            type=["pdf"],
            accept_multiple_files=True,
            key=f'files_{i}',
            help=f"Select multiple PDFs for **{st.session_state.get(f'po_{i}', '[PO]')}** to be merged. Max {MAX_FILE_COUNT} files."
        )
        st.markdown("---")

# --- PROCESS BUTTON AND DOWNLOAD AREA ---

st.markdown("### Final Step")
st.button("🚀 Process All Jobs and Create ZIP", on_click=process_all_merges, type="primary")

# Download Button Logic
if 'final_zip_data' in st.session_state and st.session_state.final_zip_data:
    st.markdown("---")
    st.subheader("✅ Download Complete")
    st.download_button(
        label=f"Download {st.session_state.final_zip_filename}",
        data=st.session_state.final_zip_data,
        file_name=st.session_state.final_zip_filename,
        mime="application/zip",
        type="primary"
    )
    st.info(f"The ZIP file name is: **{st.session_state.final_zip_filename}**")

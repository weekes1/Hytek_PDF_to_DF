import pdfplumber
import pandas as pd
import re
import os
from typing import Optional

def extract_meet_title(pdf_path: str) -> str:
    with pdfplumber.open(pdf_path) as pdf:
        first_page_text = pdf.pages[0].extract_text()
        lines = first_page_text.split('\n')
        
        # Heuristic: Look for the first line that is long and looks like a meet name
        for line in lines:
            # Example: Skip very short lines or admin headers
            if len(line) > 20 and not any(x in line.lower() for x in ['license', 'page', 'organization']):
                # Clean it a little if needed (remove trailing dates)
                line = re.sub(r'- \\d{2}/\\d{2}/\\d{4}.*', '', line)
                return line.strip()
        
        return "Unknown Meet"

def extract_hytek_results(folder_path: str, output_csv: Optional[str] = None) -> pd.DataFrame:
    """
    Extract swimming event results from a list of PDF files (Hy-tek format PDF) in a folder.
    
    Args:
        pdf_path (str): Path to a folder holding the pdf files.
        output_csv (Optional[str]): If provided, saves the results to this CSV file.
    
    Returns:
        pd.DataFrame: A DataFrame containing the parsed results.
    """
    pdf_paths = [os.path.join(folder_path, f) for f in os.listdir(folder_path) if f.lower().endswith('.pdf')]

    meet_dfs = []
    for pdf_path in pdf_paths:
        with pdfplumber.open(pdf_path) as pdf:
            text = ''
            for page in pdf.pages:
                text += page.extract_text() + '\n'

        # Split into event sections
        event_blocks = re.split(r'(?=Event \d+)', text)
        meet_title = extract_meet_title(pdf_path)

        event_dfs = []

        for block in event_blocks:
            # Find the event header
            match = re.search(r'Event (\d+)\s+(.+)', block)
            if not match:
                continue
            event_number, event_title = match.groups()

            # Find swimmer lines
            swimmer_lines = re.findall(
                r'([A-Za-z &\.\'\-]+)\s+(\d+)([A-Za-z \-\&]+)\s+([\d:\.]+)\s+([\d:\.]+)',
                block
            )

            if swimmer_lines:
                df = pd.DataFrame(swimmer_lines, columns=['Name', 'Age', 'Team', 'Finals Time', 'Seed Time'])
                df['EVENT'] = event_title
                df['EVENT_NUM'] = event_number

                # Extract details from event title
                event_text = event_title.split(' ')
                if len(event_text) >= 6:  # basic check
                    df["GENDER"] = event_text[0]
                    df["AGE_GROUP"] = event_text[1]
                    df["DISTANCE"] = event_text[2]
                    df["STROKE"] = event_text[5]
                    df['DISTANCEXSTROKE'] = event_text[2] + event_text[5]
                    df["AGE_GROUPXGENDER"] = event_text[1] + event_text[0]
                    df['MEET'] = meet_title
                
                event_dfs.append(df)

        meet_df = pd.concat(event_dfs)
        meet_dfs.append(meet_df)

    # Combine all meets into one DataFrame
    results_df = pd.concat(meet_dfs, ignore_index=True)
    results_df = results_df.map(lambda x: x.strip() if isinstance(x, str) else x)

    if output_csv:
        results_df.to_csv(output_csv, index=False)

    return results_df


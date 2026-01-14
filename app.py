import streamlit as st
import pandas as pd
import os
from datetime import datetime, timedelta
import openpyxl
from openpyxl.styles import Alignment
from io import BytesIO
import time

# --- CONFIGURATION & DATA ---
FILE_NAME = "my_placement_logs.csv"
# Expanded list of activities based on your document
ACTIVITIES = {
    "1.1": "Conduct preliminary investigations",
    "1.2": "Carry out feasibility study",
    "2.1": "Analyze current system",
    "2.2": "Identify requirements",
    "3.1": "Design data (ERD, DFD)",
    "3.2": "Design process outlines",
    "4.1": "Program design",
    "4.2": "Program code",
    "4.3": "Test programs",
    "5.1": "Testing module",
    "5.2": "Integration testing",
    "6.1": "Educate and train users",
    "9.1": "Maintenance/Bug Fixing",
    "12.1": "Project Management",
    "19.1": "Cybersecurity / Security",
    "22.1": "Cloud Computing Tasks",
    "Other": "General / Administrative"
}

# --- HELPER FUNCTIONS ---
def load_data():
    if not os.path.exists(FILE_NAME):
        df = pd.DataFrame(columns=["Date", "Day", "Week_Ending", "Activity_Code", "Description", "Problems", "Solutions"])
        df.to_csv(FILE_NAME, index=False)
        return df
    return pd.read_csv(FILE_NAME)

def save_entry(date_obj, activity_code, desc, prob, sol):
    df = load_data()
    day_name = date_obj.strftime("%A")
    # Logic: Week ends on the upcoming Sunday
    days_ahead = 6 - date_obj.weekday()
    week_ending = date_obj + timedelta(days=days_ahead)
    
    new_entry = {
        "Date": date_obj,
        "Day": day_name.upper(),
        "Week_Ending": week_ending.strftime("%Y-%m-%d"),
        "Activity_Code": activity_code,
        "Description": desc,
        "Problems": prob if prob else "",
        "Solutions": sol if sol else ""
    }
    df = pd.concat([df, pd.DataFrame([new_entry])], ignore_index=True)
    df.to_csv(FILE_NAME, index=False)
    df.to_csv(FILE_NAME, index=False)
    # st.success("Entry Saved!") # Removed to avoid clutter in bulk mode, handle in UI
    
def get_writeable_cell(ws, row, col):
    """
    Returns the writeable cell (top-left) if the target is a merged cell.
    """
    cell = ws.cell(row=row, column=col)
    if isinstance(cell, openpyxl.cell.cell.MergedCell):
        for merged_range in ws.merged_cells.ranges:
            if (col >= merged_range.min_col and col <= merged_range.max_col and
                row >= merged_range.min_row and row <= merged_range.max_row):
                return ws.cell(row=merged_range.min_row, column=merged_range.min_col)
    return cell

def get_week_start(date_obj):
    """Returns the Monday of the week for the given date."""
    return date_obj - timedelta(days=date_obj.weekday())

def fill_excel_sheet(template_file, data_df, output_path=None):
    """
    Smart function to find the right week block and fill it.
    If output_path is set, saves directly to disk. Otherwise returns bytes.
    """
    wb = openpyxl.load_workbook(template_file)
    # Assume the sheet is named 'Logs' or is the 3rd sheet. 
    # We'll try to find 'Logs' or default to active.
    if 'Logs' in wb.sheetnames:
        ws = wb['Logs']
    else:
        ws = wb.active

    # Group data by Week Ending
    grouped = data_df.groupby('Week_Ending')

    # Iterate through all rows to find "WEEK ENDING" anchors
    # We scan the first column (Column A)
    anchor_rows = []
    for row in range(1, 1000):  # Scan first 1000 rows
        # Column 1 (A)
        c1 = ws.cell(row=row, column=1)
        if c1.value:
            val_str = str(c1.value).upper()
            if "WEEK ENDING" in val_str:
                anchor_rows.append(row)
            elif "DESIGNATION" in val_str:
                c1.value = None  # Clear Designation

        # Column 2 (B) - Check if Designation is here too/instead
        c2 = ws.cell(row=row, column=2)
        if c2.value and "DESIGNATION" in str(c2.value).upper():
            c2.value = None
            
    if not anchor_rows:
        return None, "Could not find 'WEEK ENDING' blocks in the Excel file. Is it the correct format?"

    # --- FILLING LOGIC ---
    # We iterate through the weeks we have data for
    for week_date_str, group in grouped:
        target_found = False
        
        # 1. Try to find a block already labeled with this date
        for r in anchor_rows:
            date_cell = ws.cell(row=r, column=2)
            # Check if cell matches date (handling string or datetime formats)
            cell_date_str = str(date_cell.value) if date_cell.value else ""
            if week_date_str in cell_date_str:
                target_row = r
                target_found = True
                break
        
        # 2. If not found, find the first EMPTY block
        if not target_found:
            for r in anchor_rows:
                date_cell = ws.cell(row=r, column=2)
                if not date_cell.value or "____" in str(date_cell.value):  # It's empty or a placeholder! Claim it.
                    target_row = r
                    # Write the date
                    date_cell.value = week_date_str
                    target_found = True
                    break
        
        if target_found:
            # Fill Daily Entries
            # Map: Monday is Row+2, Tuesday Row+3, etc.
            day_map = {
                "MONDAY": 2, "TUESDAY": 3, "WEDNESDAY": 4, 
                "THURSDAY": 5, "FRIDAY": 6, "SATURDAY": 7, "SUNDAY": 8
            }
            
            problems_list = []
            solutions_list = []

            for _, row_data in group.iterrows():
                day_offset = day_map.get(row_data['Day'], None)
                if day_offset:
                    # Description -> Column B (2)
                    cell_desc = ws.cell(row=target_row + day_offset, column=2)
                    cell_desc.value = row_data['Description']
                    cell_desc.alignment = Alignment(wrap_text=True, vertical='top')

                    # Activity Code -> Column C (3)
                    cell_code = ws.cell(row=target_row + day_offset, column=3)
                    cell_code.value = row_data['Activity_Code']
                    cell_code.alignment = Alignment(horizontal='center', vertical='top')

                    # Collect Problems/Solutions
                    if pd.notna(row_data['Problems']) and str(row_data['Problems']).strip():
                        problems_list.append(str(row_data['Problems']))
                    if pd.notna(row_data['Solutions']) and str(row_data['Solutions']).strip():
                        solutions_list.append(str(row_data['Solutions']))

            # Fill Problems & Solutions (Row + 10)
            if problems_list:
                cell = get_writeable_cell(ws, target_row + 10, 2)
                cell.value = "\n".join(problems_list)
                cell.alignment = Alignment(wrap_text=True, vertical='top')
            if solutions_list:
                cell = get_writeable_cell(ws, target_row + 10, 3)
                cell.value = "\n".join(solutions_list)
                cell.alignment = Alignment(wrap_text=True, vertical='top')

    # Save
    if output_path:
        wb.save(output_path)
        return None, "Saved directly to file."
    
    # Save to buffer
    output = BytesIO()
    wb.save(output)
    output.seek(0)
    return output, "Success"

# --- GUI LAYOUT ---
st.set_page_config(page_title="Placement Log Automator", page_icon="🚀", layout="wide")

st.title("🚀 Industrial Placement Automator")
st.markdown("### Log daily. Generate Excel weekly.")

# Data Loading
df = load_data()

# --- TABS ---
tab1, tab2, tab5, tab3, tab4 = st.tabs(["📝 Daily Log", "📚 Bulk Backfill", "🐙 Git Import", "🤖 Excel Automator", "📊 History"])

import subprocess
import google.generativeai as genai

# --- TAB 5: GIT IMPORT ---
with tab5:
    st.header("🐙 Git History Importer")
    st.info("Scan your local git repositories to auto-generate logs from your commit history.")

    # 1. Config
    with st.expander("⚙️ Configuration", expanded=True):
        col_g1, col_g2 = st.columns(2)
        with col_g1:
            default_author = "sithikaru@gmail.com"
            author_email = st.text_input("Git Author Email", value=default_author)
        with col_g2:
            default_scan_dir = os.path.dirname(os.getcwd())
            scan_dir = st.text_input("Directory to Scan for Repos", value=default_scan_dir)
        
        gemini_api_key = st.text_input("Gemini API Key (Optional, for creative summaries)", type="password")

    # 2. Scan Logic
    if "git_repos" not in st.session_state:
        st.session_state.git_repos = []

    if st.button("🔍 Scan for Repositories"):
        found_repos = []
        try:
            subdirs = [os.path.join(scan_dir, d) for d in os.listdir(scan_dir) if os.path.isdir(os.path.join(scan_dir, d))]
            for d in subdirs:
                if os.path.exists(os.path.join(d, ".git")):
                    found_repos.append(d)
            st.session_state.git_repos = found_repos
            if found_repos:
                st.success(f"Found {len(found_repos)} git repositories!")
            else:
                st.warning("No git repositories found in this directory.")
        except Exception as e:
            st.error(f"Error scanning directory: {e}")

    # 3. Import Logic
    if st.session_state.git_repos:
        selected_repos = st.multiselect("Select Repositories to Import From", st.session_state.git_repos, default=st.session_state.git_repos)
        
        c_d1, c_d2 = st.columns(2)
        with c_d1:
            start_date = st.date_input("Start Date", datetime.today() - timedelta(days=30))
        with c_d2:
            end_date = st.date_input("End Date", datetime.today())

        if st.button("🚀 Generate Logs from History"):
            all_commits = []
            
            # Progress bar for scanning repos
            scan_progress = st.progress(0, text="Scanning repositories...")
            
            for i, repo in enumerate(selected_repos):
                repo_name = os.path.basename(repo)
                try:
                    cmd = [
                        "git", "-C", repo, "log",
                        f"--author={author_email}",
                        f"--since={start_date.strftime('%Y-%m-%d')}",
                        f"--until={end_date.strftime('%Y-%m-%d')} 23:59:59",
                        "--pretty=format:%ad|%s",
                        "--date=short"
                    ]
                    result = subprocess.run(cmd, capture_output=True, text=True)
                    if result.returncode == 0 and result.stdout:
                        lines = result.stdout.strip().split('\n')
                        for line in lines:
                            if "|" in line:
                                parts = line.split("|", 1)
                                if len(parts) == 2:
                                    date_str, msg = parts
                                    all_commits.append({
                                        "date": date_str,
                                        "message": msg,
                                        "repo": repo_name
                                    })
                except Exception as e:
                    st.error(f"Error reading {repo_name}: {e}")
                scan_progress.progress((i + 1) / len(selected_repos))
            
            if all_commits:
                commits_by_date = {}
                for c in all_commits:
                    d = c["date"]
                    if d not in commits_by_date:
                        commits_by_date[d] = []
                    commits_by_date[d].append(c)
                
                generated_logs = []
                total_days = len(commits_by_date)
                
                # Progress bar for generating summaries
                gen_progress = st.progress(0, text="Generating creative logs...")
                
                # Configure Gemini if key provided
                model = None
                if gemini_api_key:
                    try:
                        genai.configure(api_key=gemini_api_key)
                        model = genai.GenerativeModel('gemini-pro')
                    except Exception as e:
                        st.error(f"Failed to configure Gemini: {e}")

                for idx, (d_str, commits) in enumerate(commits_by_date.items()):
                    repos_touched = list(set([c["repo"] for c in commits]))
                    msgs = [c["message"] for c in commits]
                    repo_text = ", ".join(repos_touched)
                    
                    description = ""
                    prob = ""
                    sol = ""
                    
                    if model:
                        # Use Gemini
                        prompt = f"""
                        Task: Write a single, professional daily log entry (1-2 sentences) in first–person past tense based on these git commit messages found in repositories: {repo_text}.
                        Also extract any technical problems encountered and solutions applied if clear from the messages.
                        
                        Commit Messages:
                        {chr(10).join(msgs)}
                        
                        Output format (JSON):
                        {{
                            "description": "...",
                            "problem": "...",
                            "solution": "..."
                        }}
                        If no problem/solution is clear, leave them empty strings.
                        """
                        try:
                            response = model.generate_content(prompt)
                            # Simple parsing (assuming clean JSON or extracting text)
                            # Fallback to text parsing if JSON fails
                            import json
                            text = response.text
                            # Try to find JSON block
                            start = text.find('{')
                            end = text.rfind('}') + 1
                            if start != -1 and end != -1:
                                json_str = text[start:end]
                                data = json.loads(json_str)
                                description = data.get("description", "")
                                prob = data.get("problem", "")
                                sol = data.get("solution", "")
                            else:
                                description = text # Fallback
                        except Exception as e:
                            description = f"Worked on {repo_text}. {'. '.join(msgs[:3])}."
                    
                    # Fallback logic if no model or model failed
                    if not description:
                        description = f"Worked on {repo_text} repository. " + ". ".join(msgs[:5]) + "."
                        for m in msgs:
                            m_lower = m.lower()
                            if any(k in m_lower for k in ["error", "bug", "fail", "fix"]):
                                prob = "Encountered technical issues."
                                sol = f"Resolved: {m}"
                                break

                    generated_logs.append({
                        "Date": d_str,
                        "Activity": "1.1 - Software Development",
                        "Description": description,
                        "Problems": prob,
                        "Solutions": sol
                    })
                    
                    gen_progress.progress((idx + 1) / total_days)

                generated_logs.sort(key=lambda x: x["Date"])
                st.session_state.generated_git_logs = pd.DataFrame(generated_logs)
                st.success(f"Generated {len(generated_logs)} entries!")
            else:
                st.warning("No commits found.")

    # 4. Preview & Save
    if "generated_git_logs" in st.session_state and not st.session_state.generated_git_logs.empty:
        st.subheader("Preview Generated Logs")
        edited_logs = st.data_editor(st.session_state.generated_git_logs, num_rows="dynamic")
        
        if st.button("💾 Save All Imported Logs"):
            count = 0
            for index, row in edited_logs.iterrows():
                save_entry(
                    datetime.strptime(row["Date"], "%Y-%m-%d"), 
                    "1.1", 
                    row["Description"], 
                    row["Problems"], 
                    row["Solutions"]
                )
                count += 1
            
            st.success(f"Successfully imported {count} logs!")
            st.session_state.generated_git_logs = pd.DataFrame()
            time.sleep(2)
            st.rerun()

# --- TAB 1: DAILY LOG ---
with tab1:
    st.header("📝 Daily Entry")
    
    # Initialize session state for daily form reset
    if "daily_form_key" not in st.session_state:
        st.session_state.daily_form_key = 0
    
    # Key suffix for resetting
    daily_key = str(st.session_state.daily_form_key)
    
    with st.form("daily_entry_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            date_entry = st.date_input("Date", datetime.today(), key=f"date_{daily_key}")
        with col2:
            activity_code = st.selectbox(
                "Activity Code", 
                list(ACTIVITIES.keys()), 
                format_func=lambda x: f"{x} - {ACTIVITIES[x]}",
                key=f"act_code_{daily_key}"
            )
            
        description = st.text_area("Description of Work", height=100, key=f"daily_desc_{daily_key}")
        
        with st.expander("Problems & Solutions (Optional)"):
            prob = st.text_input("Problems Encountered", key=f"daily_prob_{daily_key}")
            sol = st.text_input("Solutions Finding", key=f"daily_sol_{daily_key}")
            
        submitted = st.form_submit_button("💾 Save Entry")
        
        if submitted:
            if description.strip():
                with st.spinner("Saving entry..."):
                    code = activity_code # activity_code is already the code, no split needed
                    save_entry(date_entry, code, description, prob, sol)
                    time.sleep(0.5) # Fake delay for UX
                
                st.success("✅ Entry Saved! Clearing form...")
                time.sleep(1)
                st.session_state.daily_form_key += 1
                st.rerun()
            else:
                st.error("⚠️ Description required!")


import time

# --- TAB 2: BULK BACKFILL ---
with tab2:
    st.header("📚 Bulk Week Entry")
    st.info("Select any day in a week. We'll load Monday to Friday for rapid entry.")
    
    # Initialize session state for form reset
    if "bulk_form_key" not in st.session_state:
        st.session_state.bulk_form_key = 0

    import calendar

    # Select Year and Month first
    col_y, col_m = st.columns(2)
    with col_y:
        current_year = datetime.today().year
        years = [current_year, current_year - 1]
        sel_year = st.selectbox("Year", years)
    
    with col_m:
        month_names = list(calendar.month_name)[1:]
        # Default to current month
        current_month_index = datetime.today().month - 1
        sel_month_name = st.selectbox("Month", month_names, index=current_month_index)
        sel_month = month_names.index(sel_month_name) + 1

    # Find all weeks (starting Monday) in the selected Month/Year
    week_options = []
    
    # Start checking from the 1st of the month
    # BUT we want to include a week even if it started in the previous month if the majority is in this month?
    # Or just strictly "Mondays in this month"?
    # Impl: "Mondays that fall within this month" is the clearest logic.
    
    d = datetime(sel_year, sel_month, 1)
    # Advance to the first Monday of the month
    while d.weekday() != 0: # 0 = Monday
        d += timedelta(days=1)
        
    # Collect all Mondays in this month
    while d.month == sel_month:
        w_end = d + timedelta(days=6)
        label = f"{d.strftime('%d %b')} - {w_end.strftime('%d %b %Y')}"
        week_options.append({"label": label, "start_date": d})
        d += timedelta(days=7)
    
    if not week_options:
        st.warning(f"No weeks start in {sel_month_name} {sel_year}.")
        start_of_week = datetime.today() # Fallback
    else:
        selected_option = st.selectbox(
            "Select Week", 
            week_options, 
            format_func=lambda x: x["label"]
        )
        start_of_week = selected_option["start_date"]
    
    end_of_week = start_of_week + timedelta(days=6)
    
    st.markdown(f"**Adding logs for: {start_of_week.strftime('%Y-%m-%d')} (Monday) to {end_of_week.strftime('%Y-%m-%d')} (Sunday)**")
    
    with st.form("bulk_entry_form"):
        entries = []
        activity_options = [f"{k} - {v}" for k, v in ACTIVITIES.items()]
        
        # KEY SUFFIX is crucial for resetting
        key_suffix = str(st.session_state.bulk_form_key)

        for i in range(7):
            day_date = start_of_week + timedelta(days=i)
            day_name = day_date.strftime("%A")
            
            st.markdown(f"---")
            st.subheader(f"{day_name} ({day_date.strftime('%d/%m')})")
            
            c1, c2 = st.columns([1, 2])
            with c1:
                act = st.selectbox(f"Activity ({day_name})", activity_options, key=f"act_{i}_{key_suffix}")
            with c2:
                desc = st.text_area(f"Description ({day_name})", height=70, key=f"desc_{i}_{key_suffix}", placeholder="Leave empty to skip")
            
            # Optional problems/solutions
            with st.expander(f"Problems & Solutions ({day_name})"):
                pc1, pc2 = st.columns(2)
                prob = pc1.text_input("Problem", key=f"prob_{i}_{key_suffix}")
                sol = pc2.text_input("Solution", key=f"sol_{i}_{key_suffix}")
            
            entries.append({
                "date": day_date,
                "activity": act,
                "description": desc,
                "problem": prob,
                "solution": sol
            })
        
        submitted = st.form_submit_button("💾 Save Full Week Logs")
        if submitted:
            with st.spinner("Saving entries..."):
                count = 0
                for entry in entries:
                    if entry["description"].strip():
                        code = entry["activity"].split(" - ")[0]
                        save_entry(
                            entry["date"], 
                            code, 
                            entry["description"], 
                            entry["problem"], 
                            entry["solution"]
                        )
                        count += 1
                
                time.sleep(0.5) # Fake delay for UX feel

            if count > 0:
                st.success(f"✅ Successfully saved {count} entries! Clearing form...")
                time.sleep(1)
                st.session_state.bulk_form_key += 1 # Increment key to reset widgets
                st.rerun()
            else:
                st.warning("⚠️ No descriptions entered. Nothing saved.")

# --- TAB 3: EXCEL AUTOMATOR ---
with tab3:
    st.header("Fill your IIT Record Book")
    st.info("The app will find empty weeks and fill them with your logs.")
    
    local_file_name = "Industrial Placement Record Book.xlsx"
    final_file = None
    
    # Check for local file
    if os.path.exists(local_file_name):
        st.success(f"📂 Found local file: **'{local_file_name}'**")
        if st.checkbox("Use this local file?", value=True):
            final_file = local_file_name
    
    # Fallback to uploader if no local file used
    if not final_file:
        final_file = st.file_uploader("Upload Record Book (.xlsx)", type=["xlsx"])
    
    if final_file and not df.empty:
        if st.button("⚡ Fill Excel Sheet"):
            with st.spinner("Processing..."):
                # If using the local file directly, output to the same path
                save_path = local_file_name if (final_file == local_file_name) else None
                
                processed_excel, msg = fill_excel_sheet(final_file, df, output_path=save_path)
                
                if save_path and processed_excel is None:
                    # Direct save case
                    st.success(f"✅ Record Book updated directly! ({save_path})")
                    st.balloons()
                elif processed_excel:
                    # Buffer case (uploaded file)
                    st.success("Excel Filled Successfully!")
                    st.download_button(
                        label="📥 Download Updated Record Book",
                        data=processed_excel,
                        file_name="Updated_Record_Book.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                else:
                    st.error(msg)
    elif df.empty:
        st.warning("No logs found! Go to the 'Daily Log' tab and add some entries first.")

# --- TAB 4: HISTORY ---
with tab4:
    st.dataframe(df.sort_values(by="Date", ascending=False), use_container_width=True)
    if st.button("Clear All Data (Reset)"):
        if os.path.exists(FILE_NAME):
            os.remove(FILE_NAME)
            st.rerun()
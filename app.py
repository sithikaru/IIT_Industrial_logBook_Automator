import streamlit as st
import pandas as pd
import os
from datetime import datetime, timedelta
import openpyxl
from openpyxl.styles import Alignment
from io import BytesIO
import time
from groq import Groq

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

st.title("🚀 Industrial Placement Log Book Automator")
st.markdown("### Log daily. Generate Excel weekly.")

# Data Loading
df = load_data()

# --- TABS ---
tab1, tab2, tab5, tab3, tab4 = st.tabs(["📝 Daily Log", "📚 Bulk Backfill", "🐙 Git Import", "🤖 Excel Automator", "📊 History"])

import subprocess
import requests
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# --- TAB 5: GITHUB IMPORT ---
with tab5:
    st.header("☁️ GitHub History Importer")
    st.info("Fetch commit history directly from GitHub.com to generate logs. No local .git folder needed!")

    # Load Config from Env
    gh_username = os.getenv("GITHUB_USERNAME", "")
    gh_token = os.getenv("GITHUB_TOKEN", "")
    groq_api_key = os.getenv("GROQ_API_KEY", "")

    if not gh_token:
        st.warning("⚠️ `GITHUB_TOKEN` is missing in `.env` file.")
    if not gh_username:
        st.warning("⚠️ `GITHUB_USERNAME` is missing in `.env` file.")
    if not groq_api_key:
        st.info("💡 `GROQ_API_KEY` is missing. AI summarization will be skipped. Get one free at https://console.groq.com/")

    # 2. Repo Selection
    st.subheader("Select Repositories")
    
    if "my_github_repos" not in st.session_state:
        st.session_state.my_github_repos = []

    col_btn, col_manual = st.columns([1, 2])
    with col_btn:
        if st.button("🔄 Fetch Your Repositories"):
            try:
                found_repos = []
                page = 1
                while True:
                    if gh_token:
                        # Authenticated: Get all accessible repos (private & public)
                        url = "https://api.github.com/user/repos"
                        headers = {"Authorization": f"token {gh_token}", "Accept": "application/vnd.github.v3+json"}
                        params = {"per_page": 100, "page": page, "affiliation": "owner,collaborator,organization_member", "sort": "updated"}
                    else:
                        # Public only
                        url = f"https://api.github.com/users/{gh_username}/repos"
                        headers = {"Accept": "application/vnd.github.v3+json"}
                        params = {"per_page": 100, "page": page, "sort": "updated"}
                    
                    resp = requests.get(url, headers=headers, params=params)
                    if resp.status_code == 200:
                        data = resp.json()
                        if not data:
                            break # No more pages
                        for r in data:
                            found_repos.append(r["full_name"])
                        page += 1
                        # Safety break for massive accounts (limit to 300 for now)
                        if page > 3: 
                            break
                    else:
                        st.error(f"Error fetching repos: {resp.status_code} - {resp.text}")
                        break
                
                if found_repos:
                    st.session_state.my_github_repos = sorted(list(set(found_repos)))
                    st.success(f"Found {len(found_repos)} repositories!")
                else:
                    st.warning("No repositories found.")
                    
            except Exception as e:
                st.error(f"Failed to fetch repositories: {e}")

    # Allow selection from fetched list OR manual entry
    default_options = st.session_state.my_github_repos if st.session_state.my_github_repos else ["sithija/viral-networks-fe-main", "sithija/yeheli-web-strapi-main"]
    
    selected_repos = st.multiselect(
        "Choose Repositories", 
        st.session_state.my_github_repos if st.session_state.my_github_repos else default_options,
        default=[] # Start empty so user can choose
    )
    
    # Fallback for manual addition if fetch fails or repo missing
    if not st.session_state.my_github_repos:
        st.caption("Or type manually below if fetch fails:")
        manual_entry = st.text_area("Manual Repo List (owner/repo)", height=68, 
                                    value="sithija/viral-networks-fe-main\nsithija/yeheli-web-strapi-main")
        if manual_entry:
            manual_list = [r.strip() for r in manual_entry.split('\n') if r.strip()]
            # Combine unique
            selected_repos = list(set(selected_repos + manual_list))

    # 3. Import Logic
    c_d1, c_d2 = st.columns(2)
    with c_d1:
        start_date = st.date_input("Start Date", datetime.today() - timedelta(days=30))
    with c_d2:
        end_date = st.date_input("End Date", datetime.today())

    scan_all_branches = st.checkbox("🕵️‍♀️ Scan ALL branches (Slow)", value=False, help="Check this to find commits on unmerged feature branches.")
    
    use_author_filter = True
    if gh_username:
        use_author_filter = st.checkbox(f"Filter by author: {gh_username}", value=True, help="Uncheck to see commits from everyone.")

    if st.button("🚀 Fetch & Generate Logs"):
        if not selected_repos:
            st.error("Please select at least one repository.")
        else:
            headers = {"Accept": "application/vnd.github.v3+json"}
            if gh_token:
                headers["Authorization"] = f"token {gh_token}"
            
            all_commits = []
            seen_shas = set() # To store unique commit SHAs

            progress_bar = st.progress(0)
            status_text = st.empty()
            
            total_repos = len(selected_repos)
            
            for i, repo in enumerate(selected_repos):
                # Determine branches to scan
                branches = []
                if scan_all_branches:
                    status_text.text(f"Listing branches for {repo}...")
                    try:
                        br_url = f"https://api.github.com/repos/{repo}/branches"
                        br_resp = requests.get(br_url, headers=headers)
                        if br_resp.status_code == 200:
                            branches = [b["name"] for b in br_resp.json()]
                        else:
                            st.warning(f"Could not list branches for {repo}, defaulting to main.")
                            branches = [None]
                    except:
                        branches = [None]
                else:
                    branches = [None] # None means default branch

                for branch_name in branches:
                    branch_label = branch_name if branch_name else "default"
                    status_text.text(f"Fetching {repo} [{branch_label}]...")
                    
                    try:
                        # Pagination Loop
                        page = 1
                        while True:
                            url = f"https://api.github.com/repos/{repo}/commits"
                            params = {
                                "since": start_date.strftime('%Y-%m-%dT00:00:00Z'),
                                "until": (end_date + timedelta(days=1)).strftime('%Y-%m-%dT00:00:00Z'),
                                "per_page": 100,
                                "page": page
                            }
                            # Apply Author Filter IF checkbox is checked
                            if gh_username and use_author_filter:
                                params["author"] = gh_username
                                
                            if branch_name:
                                params["sha"] = branch_name
                            
                            resp = requests.get(url, headers=headers, params=params)
                            
                            if resp.status_code == 200:
                                commits = resp.json()
                                if not commits:
                                    break # No more commits
                                
                                for c in commits:
                                    sha = c["sha"]
                                    if sha in seen_shas:
                                        continue # Skip duplicate
                                    seen_shas.add(sha)
                                    
                                    commit_date_str = c["commit"]["author"]["date"]
                                    dt_obj = datetime.strptime(commit_date_str, "%Y-%m-%dT%H:%M:%SZ")
                                    date_only = dt_obj.strftime("%Y-%m-%d")
                                    msg = c["commit"]["message"]
                                    
                                    all_commits.append({
                                        "date": date_only,
                                        "message": msg,
                                        "repo": repo
                                    })
                                
                                # Optimization: If fewer than 100 results, we reached end
                                if len(commits) < 100:
                                    break
                                page += 1
                                # Limit pages to prevent infinite loops on massive repos
                                if page > 20: 
                                    break
                                    
                            elif resp.status_code == 409:
                                break # Empty repo
                            else:
                                st.warning(f"Failed {repo}/{branch_label}: {resp.status_code}")
                                break
                            
                    except Exception as e:
                        st.error(f"Error fetching {repo}: {e}")
                
                progress_bar.progress((i + 1) / total_repos)

            status_text.text("Processing logs...")
            # Group by Date
            commits_by_date = {}
            for c in all_commits:
                d = c["date"]
                if d not in commits_by_date:
                    commits_by_date[d] = []
                commits_by_date[d].append(c)
            
            # Summarize
            if not commits_by_date:
                st.warning("No unique commits found matching your criteria.")
            else:
                generated_logs = []
                total_days = len(commits_by_date)
                
                gen_progress = st.progress(0, text="Summarizing with AI..." if groq_api_key else "Summarizing...")
                
                # Initialize Groq Client
                groq_client = None
                if groq_api_key:
                    try:
                        groq_client = Groq(api_key=groq_api_key)
                    except Exception as e:
                        st.error(f"Groq Init Error: {e}")

                for idx, (date_str, commits) in enumerate(sorted(commits_by_date.items(), reverse=True)):
                    repos_touched = list(set([c["repo"] for c in commits]))
                    msgs = [c["message"] for c in commits] # Use ALL messages for context
                    
                    repo_text = ", ".join([r.split('/')[-1] for r in repos_touched]) # Just repo name
                    
                    description = ""
                    prob = ""
                    sol = ""
                    
                    if groq_client:
                        # Groq free tier is generous (14,400 RPD), but still add a small delay
                        time.sleep(1) 
                        prompt = f"""Role: Professional developer writing a daily work log.
Context: Worked on {repo_text}.
Input Commits:
{chr(10).join(msgs)}

Task:
1. Summarize the work done into 1-2 professional sentences (first-person past tense). 
2. Identify ONE key technical challenge/bug if present.
3. Identify the solution used.
4. **Select the most appropriate Activity Code** from the list below based on the work done:

**Activity Codes:**
1.1 - Conduct preliminary investigations
2.1 - Analyze current system
2.2 - Identify requirements and deficiencies
2.3 - Specify requirements of proposed system
3.2 - Design process outlines
3.3 - User Interfaces/UX/HCI
3.9 - UI Planning
3.10 - Design/Develop Interactive UI Elements
4.1 - Program design
4.2 - Program code
4.3 - Test programs
4.4 - Customization of package & software
5.1 - Testing module
5.2 - Integration testing
5.3 - System testing
6.4 - Installation of software (Deployment)
7.3 - Quality Assurance (Implementation stage)
8.4 - Security
9.1 - Document and/or update documentation
9.2 - Conduct maintenance review and enhancement
10.2 - Networking Implementation
12.1 - Project planning
19.2 - Implement security protocols
19.4 - Respond to security incidents
20.2 - Perform data analysis
20.4 - Manage databases
21.1 - Develop machine learning models
21.2 - Implement AI algorithms
22.2 - Implement cloud solutions
23.1 - Develop software applications (general)
23.2 - Implement DevOps practices
23.5 - Conduct code reviews
24.1 - Manage online store operations

**Selection Guide:**
- Bug fixes, refactoring, feature additions -> 4.2 (Program code)
- UI/UX work, frontend changes -> 3.3 or 3.10
- Testing, QA -> 4.3 or 5.1
- Deployment, CI/CD -> 6.4 or 23.2
- Documentation -> 9.1
- Security patches -> 19.2
- Database changes -> 20.4
- AI/ML work -> 21.1 or 21.2

Output ONLY valid JSON (no markdown, no extra text):
{{
    "description": "...",
    "problem": "...",
    "solution": "...",
    "activity_code": "X.X"
}}"""
                        try:
                            response = groq_client.chat.completions.create(
                                model="llama-3.3-70b-versatile",
                                messages=[{
                                    "role": "user",
                                    "content": prompt
                                }],
                                temperature=0.3,
                                max_tokens=500
                            )
                            text = response.choices[0].message.content
                            # Parse JSON from response
                            start = text.find('{')
                            end = text.rfind('}') + 1
                            if start != -1 and end != -1:
                                data = json.loads(text[start:end])
                                description = data.get("description", "")
                                prob = data.get("problem", "")
                                sol = data.get("solution", "")
                                activity_code = data.get("activity_code", "4.2")
                            else:
                                description = text
                                activity_code = "4.2"
                        except Exception as e:
                            st.warning(f"⚠️ AI Error on {date_str}: {e}")
                            description = f"Contributed to {repo_text}. Updates include: {msgs[0]}."
                            activity_code = "4.2"
                    
                    if not description:
                        description = f"Development work on {repo_text}. Key changes: {msgs[0]}."
                        if len(msgs) > 1:
                            description += f" Also worked on {msgs[1]}."
                        activity_code = "4.2"  # Fallback

                    generated_logs.append({
                        "Date": date_str,
                        "Activity": activity_code,
                        "Description": description,
                        "Problems": prob,
                        "Solutions": sol
                    })
                    gen_progress.progress((idx + 1) / total_days)

                generated_logs.sort(key=lambda x: x["Date"])
                st.session_state.generated_git_logs = pd.DataFrame(generated_logs)
                st.success(f"✅ Generated {len(generated_logs)} entries via GitHub API!")

    # 4. Preview & Save (Same as before)
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
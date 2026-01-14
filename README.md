# 🚀 Industrial Placement Log Book Automator

A powerful Streamlit application designed to automate the creation of daily placement logs using GitHub commit history and AI summarization.

## ✨ Key Features

-   **🤖 AI-Powered Auto-Fill**: Automatically fetches your GitHub commits and generates professional, human-like daily summaries using Groq AI (Llama 3).
-   **📁 GitHub Integration**: Fetches commits directly from your repositories, allowing filtering by date, branch, and author.
-   **⚡ Smart Caching**: Save fetched commits locally to avoid repeated API calls and speed up processing.
-   **📊 Excel Report Generation**: Generates a formatted Excel record book compatible with university templates, including weekly grouping and problem/solution sections.
-   **📝 Manual Entry**: fallback options for manual daily or weekly bulk entries.
-   **💾 Persistence**: Saves all logs locally to `my_placement_logs.csv` so you never lose data.

---

## 🛠️ Setup & Installation

### 1. Prerequisites
-   Python 3.8 or higher.
-   A GitHub Account (and a Personal Access Token).
-   A [Groq API Key](https://console.groq.com/) (for AI features).

### 2. Installation
Clone the repository and install the dependencies:

```bash
pip install -r requirements.txt
```

### 3. Environment Configuration (`.env`)
Create a file named `.env` in the root directory and add your keys. This is crucial for the app to function.

```ini
# Required for fetching private/public repos
GITHUB_USERNAME=your_github_username
GITHUB_TOKEN=your_github_personal_access_token

# Required for AI Summarization
GROQ_API_KEY=gsk_your_groq_api_key_here
```

#### 🔑 How to get these keys:

**1. GitHub Personal Access Token (Classic)**
   - Go to **GitHub Settings** > **Developer settings** > **Personal access tokens** > [**Tokens (classic)**](https://github.com/settings/tokens).
   - Click **Generate new token (classic)**.
   - Give it a Note (e.g., "LogBook").
   - **Scopes**: Check the **`repo`** box (Full control of private repositories). This is required to read your commits.
   - Click **Generate token** and copy the string starting with `ghp_`.

**2. Groq API Key**
   - Go to the [Groq Console](https://console.groq.com/keys).
   - Sign in with your email or GitHub.
   - Click **Create API Key**.
   - Copy the key starting with `gsk_`.

> **Note**: If you don't provide a `GROQ_API_KEY`, the app will simply list your commit messages without summarizing them.

---

## 🚀 How to Run

Run the application using Streamlit:

```bash
streamlit run app.py
```

The app will open automatically in your default web browser (usually at `http://localhost:8501`).

---

## 📖 User Guide

### 1. 🤖 Bulk Auto-Fill (Git) - *Recommended*
This is the main feature. It looks at your code commits and writes your logs for you.

1.  **Select Date Range**: Choose the Start and End date you want to generate logs for.
2.  **Fetch Repositories**: Click to load your GitHub repositories.
3.  **Choose Repos**: Select the specific repositories you worked on during that period.
    *   *Option: Check "Filter by author" to ensure only YOUR commits are used.*
    *   *Option: Check "Scan ALL branches" if you work on feature branches (slower).*
4.  **Data Source**:
    *   **Fetch from GitHub**: Gets fresh data from the API and saves a backup.
    *   **Use Cached Data**: Loads instantly from the previous fetch (useful if you are iterating on the prompt).
5.  **Generate**: Click **fetch & Generate Logs**.
    *   The AI will process your commits and generate a table.
    *   It will automatically detect the **Project Name** from your repo name.
    *   It will write a natural summary (e.g., *"I implemented the login for [Project]..."*).
6.  **Review & Save**: Edit any entries in the preview table if needed, then click **Save to Record Book**.

### 2. 📝 Daily Log
Use this for days where you didn't push code or need to add a manual entry.
-   Select the Date and Activity Code.
-   Write a description.
-   (Optional) Add Problems Encountered and Solutions.
-   Click **Add Entry**.

### 3. 🗓️ Manual Weekly Fill
Useful for backfilling older weeks quickly without Git data.
-   Select the Month and Year.
-   Fill in details for Monday-Sunday.
-   Click **Save Week**.

### 4. ⚙️ Excel Automator
This generates the final file you submit to university.
1.  **Upload Template**: Upload your university's `.xlsx` template file.
    *   *The app expects a "WEEK ENDING" pattern in the template to locate where to write.*
2.  **Select Date Range**: Choose the months you want to export.
3.  **Download**: Click **Generate Excel** to get your filled file.

### 5. 📜 History
-   View all your saved logs in a master table.
-   Sort by date to see your progress.
-   **Clear All Data**: Use the danger button to reset `my_placement_logs.csv` (Warning: This cannot be undone).

---

## 💡 Troubleshooting

-   **"Rate Limit Exceeded"**: If GitHub blocks you, wait a few minutes or ensure your `GITHUB_TOKEN` is valid.
-   **"Groq Error"**: Check your `GROQ_API_KEY`. If the AI is hallucinating, try reducing the batch size in the code or fetching fewer days at a time.
-   **"KeyError: Date"**: This means your history file is empty. Add a log entry to fix it.

# MediMochi
A tiny medical knowledge buddy, powered by LLMs. Making healthcare technology easier to understand, one term at a time.

MediMochi reads a PDF, finds the terms that belong to a field you choose (software in the medical field by default, but it can be finance, law, anything), looks up each term's meaning on the web, and saves everything with a source link to `terms.csv`.

![MediMochi demo: running the tool on a scanned PDF, with the cost warning, the cost estimate, the two confirmation questions and the final cost summary](media/demo.gif)

*A real run on a scanned PDF: the cost warning, the estimate, the two `Continue? [y/N]` questions, the saved terms and the final cost summary.*

> [!WARNING]
> **⚠️ Scanned PDFs can be very expensive.**
> If a PDF has no text (a scan, or photos of pages), MediMochi reads **every page as an image**. Image reading costs much more than text, and the cost grows with every page, so a long document can get costly fast. The tool shows a big red warning when this happens, and it always shows a cost estimate and asks you to confirm (`y` or `n`) before it sends anything to OpenAI. Check the page count first, and use a text version of the document whenever you can.

## Why I built this

When I read academic papers or technical documents outside my area of expertise, unfamiliar terminology keeps breaking my flow. I either forget what a term meant halfway through, or I stop reading to search for its definition.

MediMochi fixes that up front. Before reading a document, I run it to extract the important terms and generate a CSV dictionary with explanations and sources. I skim the terms beforehand and come back to the dictionary whenever I need a refresher, so I spend less time looking things up and more time understanding what I'm reading.

## What it does

1. **Reads the PDF.** It reads the document's text first. Only if the PDF has no text at all (for example a scan) does it send the pages as images. This costs much more, so the tool prints a warning when it happens.
2. **Estimates the cost and asks before spending anything.** It shows a rough cost estimate and asks `Continue? [y/N]`. Answer `n` and nothing is sent to the model and nothing is charged.
3. **Finds the terms** that relate to your field, including standards, regulations and procedures (for example IEC 62304).
4. **Removes unrelated terms** with one cheap check, and prints which ones it dropped, so you don't pay to search for them.
5. **Asks again before the web searches.** Once it knows exactly how many terms there are, it shows the cost of looking them up and asks `Continue? [y/N]` a second time. Answer `n` to stop here: you keep the list of terms it found, and only the cheap first steps are charged.
6. **Looks up each meaning on the web** and keeps the link of the page it used.
7. **Saves a CSV** and prints how many tokens it used and an estimated cost for the run, so you can keep an eye on your spending.

## What you need

- **Python 3.10 or newer** (check with `python --version`; on Windows try `py --version`). Download it from [python.org](https://www.python.org/downloads/) if you don't have it.
- **An OpenAI API key** with some credit on the account. You can create one at [platform.openai.com/api-keys](https://platform.openai.com/api-keys). This is separate from a ChatGPT subscription.
- **A PDF** to read.

## Setup, step by step

### 1. Download the project

With Git:

```
git clone https://github.com/Jiawen-Wang06/MediMochi.git
cd MediMochi
```

Without Git: open the repository page on GitHub, choose **Code → Download ZIP**, unzip it, and open a terminal inside the unzipped `MediMochi` folder.

### 2. Create and activate a Python environment (recommended)

A virtual environment keeps this project's packages separate from the rest of your computer. Create it once, inside the `MediMochi` folder:

| System | Create it |
|---|---|
| Windows | `py -m venv venv` |
| macOS / Linux | `python3 -m venv venv` |

Then activate it. You need to do this every time you open a new terminal:

| System | Activate it |
|---|---|
| Windows (PowerShell) | `.\venv\Scripts\Activate.ps1` |
| Windows (Command Prompt) | `venv\Scripts\activate.bat` |
| macOS / Linux | `source venv/bin/activate` |

When it works, your prompt starts with `(venv)`. From here on, `python` and `pip` refer to this environment on every system.

> **PowerShell says "running scripts is disabled"?** Run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` (it only affects that one window) and activate again, or use Command Prompt instead.

### 3. Install the packages

```
pip install -r requirements.txt
```

This installs `openai`, `pymupdf`, `click`, `python-dotenv`, `tenacity` and `tiktoken`. The OpenAI package must be version 1.66 or newer, which `requirements.txt` already asks for.

### 4. Set up your OpenAI API key

Never share your key or commit it to Git. Choose **one** of these options.

**Option A: a `.env` file (recommended, the same on every system)**

Create a file named exactly `.env` in the `MediMochi` folder, next to this README, containing one line:

```
OPENAI_API_KEY=paste-your-key-here
```

No quotes and no spaces around the `=`. You can create it from a terminal inside the `MediMochi` folder:

| System | Command |
|---|---|
| Windows (PowerShell) | `Set-Content -Path .env -Value "OPENAI_API_KEY=paste-your-key-here"` |
| macOS / Linux | `echo 'OPENAI_API_KEY=paste-your-key-here' > .env` |

If you use a text editor instead, make sure the file is saved as `.env` and not `.env.txt` (Windows Notepad adds `.txt` unless you choose "All files"). The tool looks for `.env` in the `MediMochi` folder or the `medimochi_code` folder, wherever you run the command from. The project's `.gitignore` already keeps `.env` out of Git.

**Option B: an environment variable**

| System | This terminal session only | Permanent |
|---|---|---|
| Windows (PowerShell) | `$env:OPENAI_API_KEY="paste-your-key-here"` | `setx OPENAI_API_KEY "paste-your-key-here"` then open a **new** terminal |
| Windows (Command Prompt) | `set OPENAI_API_KEY=paste-your-key-here` | `setx OPENAI_API_KEY "paste-your-key-here"` then open a **new** terminal |
| macOS (zsh) | `export OPENAI_API_KEY="paste-your-key-here"` | add that line to `~/.zshrc`, then run `source ~/.zshrc` |
| Linux (bash) | `export OPENAI_API_KEY="paste-your-key-here"` | add that line to `~/.bashrc`, then run `source ~/.bashrc` |

If both are set, the environment variable wins over `.env`.

### 5. Run it

Go into the code folder and run the tool with your PDF:

```
cd medimochi_code
python cli.py --file "path/to/your/document.pdf"
```

## Usage

```
python cli.py --file "path/to/document.pdf" ["field or topic"] [--model gpt-4o-mini] [--yes]
```

| Part | Meaning |
|---|---|
| `--file` | **Required.** The PDF to read. Put the path in quotes if it contains spaces. |
| `"field or topic"` | Optional. What kind of terms to extract, in your own words, for example `"Finance field"`, `"cybersecurity"` or `"contract law"`. Defaults to `software in the medical field`. |
| `--model` | Optional. `gpt-4o-mini` (default, cheaper) or `gpt-4o`. |
| `--yes` or `-y` | Optional. Skips the two `Continue? [y/N]` cost questions and goes ahead automatically. Only use it when you already know what the run will cost. |

Run `python cli.py --help` to see this list in your terminal.

## Example

Extract the finance terms from a document:

```
python cli.py --file "C:\Users\you\Documents\fintech-paper.pdf" "Finance field"
```

On macOS or Linux:

```
python cli.py --file "$HOME/Documents/fintech-paper.pdf" "Finance field"
```

The output looks like this (shortened, and the numbers are only for illustration):

```
Using model: gpt-4o-mini
Field: Finance field

fintech-paper.pdf: 12 page(s); reading the text of 12 page(s)

Cost estimate (rough, based on the prices in config.py):
  Step 1, finding terms:  2 request(s), about ... input tokens, about $...
  Step 2, web lookups:    about $0.0113 per term (one web search each)
  The number of terms is not known yet. You will be asked again, with the exact number, before any web search.
Continue? [y/N]: y

  pages 1-7: 18 term(s)
  pages 8-12: 11 term(s)

Checking which of 27 term(s) belong to "Finance field"...
  21 of 27 term(s) kept
  Removed as unrelated: ...

21 term(s) are ready to be looked up on the web.
  Estimated cost of the lookups: about $0.2373 (21 x about $0.0113)
  Estimated cost so far:         about $...
Continue? [y/N]: y

Looking up 21 term(s) on the web...
  [1/21] derivatives
  [2/21] hedging
  ...

{
  "terms": [
    {
      "term": "derivatives",
      "definition": "A financial contract whose value depends on ...",
      "source": "https://..."
    }
  ]
}

Saved 21 term(s) to terms.csv (replacing any previous file)

──────────────────────────────────────────────────
Latency:       ...
Input tokens:  ...
Output tokens: ...
Web searches:  21 ($0.2100)
Est. cost:     ... (tokens ... + searches)
Total tokens:  ...
```

## Output: `terms.csv`

The results are saved in `terms.csv` in the folder you ran the command from, with these columns:

| Column | Contents |
|---|---|
| Term | The term found in the document |
| Definition | A short meaning found on the web |
| Source | The web page the definition came from |
| Field | The field you asked for |
| Document | The PDF the term came from |

- **Each run replaces the previous `terms.csv`.** Copy the file somewhere else first if you want to keep it.
- If a run fails, or finds no related terms, the existing `terms.csv` is left untouched.
- The file opens correctly in Excel, including special characters.

## Cost

**You are asked before anything is spent.** The tool shows a cost estimate and asks `Continue? [y/N]` before sending anything to the model, then asks again with the exact number of terms before the web searches, which are the main cost. Pressing Enter, typing `n`, or closing the input all count as "no": the tool stops, and nothing further is sent or charged. The estimate for reading pages as images is rougher than the one for text, because OpenAI's image pricing is harder to predict.

Every run also prints its token counts and an **estimated** cost at the end, so you can monitor your spending as you go. It is only an estimate: it is calculated from the prices stored in `medimochi_code/config.py` plus an assumed $0.01 per web search, which may differ from what OpenAI actually bills. Check the usage page of your OpenAI account for the real amount, and update the prices in `config.py` if they change.

The main cost is the web search for each term, plus the tokens the search reads. Ways to keep costs down:

- Use a specific field name, so fewer unrelated terms reach the web search step.
- Keep the default `gpt-4o-mini` model.
- Prefer PDFs with real text. If a PDF has no text (a scan, for example), the tool reads **every page as an image** and prints a warning first. Image reading is much more expensive than text, and the cost grows with every page, so a long scanned document can get costly. If you can, use a text version of the document instead.

## Troubleshooting

| Problem | What to do |
|---|---|
| `OPENAI_API_KEY is not set` | Check that `.env` is in the `MediMochi` folder, is named `.env` (not `.env.txt`), and contains `OPENAI_API_KEY=your-key`. If you used `setx`, open a new terminal. |
| `ModuleNotFoundError: No module named ...` | The environment isn't active or the packages aren't installed. Activate it (your prompt should start with `(venv)`) and run `pip install -r requirements.txt`. |
| The web search was rejected for the model | Make sure your OpenAI account has credit and that the model supports web search. Try `--model gpt-4o`. |
| `No terms related to "..." were found` | The document may not cover that field. Try a broader wording. `terms.csv` was not changed. |
| `Cannot write to ...terms.csv` | Close `terms.csv` if it is open in Excel (or another program), then run again. The tool checks this before it starts, so nothing is searched or charged. If the file gets locked during a run, your results are saved to `terms_<date>_<time>.csv` instead of being lost. |
| A term shows `(no web source found)` | The search found no page to cite. It is saved with an empty Source, so check it by hand. |
| Rate limit errors | The tool retries automatically. If it keeps failing, wait a minute and run again. |

## Project layout

```
medimochi_code/
  cli.py          the command-line tool
  pdf_reader.py   reads PDF text (or page images)
  relevance.py    drops terms unrelated to the field
  lookup.py       looks up each term's meaning on the web
  llm_client.py   talks to the OpenAI API
  export.py       writes terms.csv
  config.py       models, prices, default field
  utils.py        token counting and cost helpers
```

# MassiBot

This is the Artifact created in my Design Science Research double theses for MBA and MEng. It is a snapshot of the situation at the time of finishing. It will not be updated to keep all the mistakes and other funny things referred to in the theses.

MBA thesis: *link incoming*
MEng thesis: *link incoming*

Tech in short:

**LangChain** run on **LangGraph** and **FastAPI** server integrated to minimal **Django** app utilizing **Htmx** and **Bootstrap**. Common **PostgreSQL** db and **Redis** cache for both. Comes with dev environment for **GitHub Codespaces** or local. **GitHub Actions** to deploy to **Azure Functions**.

## Structure

Short guide to folder structures and important files for faster navigation

### bot

The main code of the agents. Separated to folders by Design Cycle, named and commented to find code referred in thesis. `api.py` in this folder has major significance as the FastAPI backend for the bot.

### chat + web

Django installation. `web` is the main folder and `chat` is the app. `views.py` for the main backend logic and for the Htmx-hack `message.html` is worth a look.

### dev

Files to test and tweak, especially the scratch files for interactive Python-thinking. Some tips in the bottom of this readme.

#### dev/data

Script for scraping the knowledge base documents and the vector database creation

#### dev/fine_tuning

Files related to fine-tuning of Mistral and Llama. Note: fine-tuning Mistral was done in a project `mistral-finetune` they offer, but settings file `7B.yaml` offered for reference here.

## Dev environment

Have Python 3.11 environment (**Pyenv** highly recommended) set up along with **Docker**. Running in GitHub Codespace this is done for you automagically.

>Note: Using **WSL2** for development environment on your Windows gaming rig is a good way to get some *oomph* to your **Machine Learning** projects.

### Prerequisites

#### Local

`requirements.txt` int the root includes Python packages needed.

Create `.env` file to root with following parameters, changing `<values>` accordingly (there is `.env_template` to help):

    BOT_URL=127.0.0.1:2024
    DB_URI=postgresql://<dbuser>:<dbpwd>@127.0.0.1/<dbname>?sslmode=disable
    DB_URIP=postgresql+psycopg://<dbuser>:<dbpwd>@127.0.0.1/<dbname>?sslmode=disable
    DB_NAME=<dbname>
    DB_USER=<dbuser>
    DB_PASSWORD=<dbpwd>
    DB_HOST=127.0.0.1
    DJANGO_SECRET_KEY=<generatelongstring>
    LANGSMITH_API_KEY=<yourlangsmithkey>
    MASTER_KEY=<generatesupersecretkey>
    OPENAI_API_KEY=<youriopenaikey>
    REDIS_URI=redis://127.0.0.1:6379/0
    TAVILY_API_KEY=<yourtavilykey>
    LANGCHAIN_TRACING_V2=true

Start up database and cache into a dedicated terminal window:

    docker compose up

#### Codespaces

Add environment values as secrets in *Settings -> Secrets and variables -> Codespaces* in your GitHub repository.

Start the Codespace as per usual under the green *Code* dropdown. `devcontainer.json` takes care of the rest.

>Note: Be mindful of used core hours! Blasted away my hours in a week without noticing.

### Running

If it is a fresh environment run few Django things first:

    cd web
    python manage.py migrate
    python manage.py createsuperuser

Next, in two separate terminal windows:

#### Bot

    cd bot
    langgraph dev

#### Web

    python manage.py runserver

**That's it!**

Now you can navigate to `http://127.0.0.1:8000` (or the Codespace port forwarded one), log in with your user you created and start chatting.

To view LangGraph API docs, navigate to `http://127.0.0.1:2024/docs`. Note that using the API requires the `MASTER_KEY` you created added to *Authorization* header.

### dev folder

Very handy way to try out code is iPython interactive window. *notebook* package and *Jupyter* extension installed`settings.json` has the critical setting enabled, so painting text or full row using **SHIFT+Enter** opens run to a new window. This is what the `*scratch.py` files are for.

If you want to try only the graph without setting up servers, edit the `bot_run.py` file with good *thread_id* and run it in a terminal. Type `quit`, `exit` or `q` to stop. EDIT: Now broken, avoid.

To fiddle with `.html` files and **Htmx**, a very handy extension for VSCode is the **Live Server**.


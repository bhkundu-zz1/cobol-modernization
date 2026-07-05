
## software architecture expectations
I want to build an software application as harness with solid scalable design to produce research, input, recommendation as guidance for clients to implement COBOL application migration strategy. This harness will developed with ui in react, api in python and database as couchdb; There will be agents powered by both open source and commercial LLMs to read COBOL, JCL code to reason, infer and share input as recommendation to write features as epics and stories. The goal is :
1. migrate COBOL as microservices in either python or java springboot api with thoughful recommendation. 
2. migrate JCL as python scripts that can be scheduled as a unix shell scripts or cron jobs via apache airflow

There should be a LLM gateway like LiteLLM thru which models can be plugged or switched as needed into the harness. There should be guardrails based on NViDIA nemo; agents should follow anthropic skills and tools folder structure so that users can update skills as markdown files; Langfuse should be used for agent observability; so appropriate logging and exception mechanism must be there as non-functional requirements as part of architceture; end to end response time in react must be less than 5 seconds, error rate must be less than 1 %; logging and auditing must support financal and regulatory compliance guideline in USA set by SEC and US treasury department who regulates ban and financial services companines. can u include these as constraint and update the document; 

## other instrcutions 
don't publish anything in github unless specifically instructed. github repo is [text](https://github.com/bhkundu-zz1/cobol-modernization.git)

Always update the architecture.md before publishing into github

Always use .env file to define environment variables; read from it at any application layer or component; this is to avoid any hardcoding and separate code from configuration

Always create unit tests scenarios, test scripts for python code in the respective test folder inside backend; always run unit test as the best practice after writing code

Always create unit tests scenarios, test scripts for reactJS code in the respective test folder inside frontend; always run unit test as the best practice after writing code; ReactJS code should be following micro frontend philosophy of development. If required, create backend for frontend(BFF) using python as required to serve the page to satisfy user journey; if there are values frequently used, please create cache; if an micro frontend is down, whole application must not be down. each micro frontend must be individually deployable as a self-contained app running in a specific port.


Agents should have skills in skills folder as markdown files; agents will access data, api via mcp gateway; agents behavior should be observable. There should be kill command to kill any agents in case of emergency.



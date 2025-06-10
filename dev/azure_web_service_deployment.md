# Azure Deployment that does not work

Below, a workflow I wrote for Azure deployment with Web Service, that was with some success tried before using serverless functions. Here as reminder if some brainfreeze happens to try it again.

## The guide

Create Resource Group
* Pick suitable Region (I chose North Europe) and use the same Region wherever applicable.
* Resource Group makes it easy to clean resources if you make a mistake (you will, I nailed architecture stack at 6th try or so).

Create Web App + Database
* Pick the template "Web App + Database" from Azure marketplace (under +create in Resource Group), name it "massibot"
* This creates automatically many handy things othwerwise cumbersome to configure, like *App Service Plan*, *Managed Identity*, *RBAC roles*, *Vnet*, *Private Endpoint*
* Choose PostgreSQL Flexible, Redis and Basic hosting plan. This is the cheapest development setup (with Azure templates it is not always so).
* This will be for the Django app and deployment will be via code (there is no way to choose container with this template).
* From Deployment Center, link Github Actions, but cancel workflow and remove .yml since it does not work out of the box. This step however creates Federated Identity to new Managed Identity. Note: Azure created repository actions secrets and environment. Leave them as they are and edit the workflow in this folder, or modify the secrets (AZURE_CLIENT, AZURE_TENANT, AZURE_SUBSCRIPTION, found from the Managed Identity).
* In App Service Logs, enable File System logging.
* At Identity, pick System assigned and set it to "On".

todo: note about Github Environments somewhere

Create Container Regristry
* Create under +create in Resource Group.
* After creation, enable Admin user from Access keys and store credentials to Github Repository (more precisely as ACR_PWD).
* Run "Bot Build & Push" workflow in Github Actions via workflow_dispatch (or alternatively build image yourself with *langgraph build* and push).
* You see **massibot-graph:latest** in Repositories

Create Web App for Container
* Create (Web App) under +create in Resource Group, name it "massibot-graph"
* Select "Container" and the App Service Plan created earlier.
* Select Azure Container Registry and search the image you pushed earlier
* Select network injection and the Vnet created eariler. Pick ready made Subnet for outbound access.
* After creation the app wont start since it is missing many environment variables and access to Container Registry.
* At Identity, pick System assigned to on and go to Container Registry IAM to assign role **AcrPull** to created System-assigned Managed Identity.
* Back in massibot-graph Deployment Center, check Continous deployment "On" so a Webhook is created for you and change Authentication to System assigned. Also enable SCM basic authentication so that Container Registry can ping the Webhook and updat the Webhook with correct URL.
* In App Service Logs, enable File System logging.
* Connect massibot-graph to PostgreSQL and Redis via Service Connector interface. With Redis, use the created Private Endpoint. Validate the connections.
* At PostgreSQL Server parameters *azure.extensions*, enable `BTREE_GIN` and `LTREE` for LangGraph to work.

Create Key Vault
* Use same region and pick the standard tier.
* Use RBAC and on networking tab deselect public access and create a new private endpoint.
* After creation, go to IAM and give your user Key Vault Administrator role so you can create secrets. While at it, add both Web App System-assigned Madaged Identity to role Key Vault Secrets User.
* Got to networking and add Firewall exception to your IP if creating secret gives access error. This is due access limited to private endpoint only.
* Create secrets according to .env list above. Use safe, new values, not the ones for local development.

Connect Web App secrets to Key Vault
* For both massibot and massibot-graph, add environmet variables in format `@Microsoft.KeyVault(VaultName=massibot-keyvault;SecretName=master-key)`. Green checkmark means working connection.
* Remove at least plain text secrets fron environmet variables.

Deploy both LangGraph and Django
* Extra: go to created Webhook and *Ping*. 202 means it is working and massibot-graph is deploying container.
* Run "Bot Build & Push" workflow in Github Actions via workflow_dispatch to verify the image gets updated, Webhook pinged and container updated in massibot-graph.
* Run "Web Build & Deploy" workflow and wait awhile for Oryx build to do its magic at Azure runner.
* First time deployment for Django requires to connect via SSH and run `migrate` and `createsuperuser` with *manage.py*. `collectstatic` is ran automatically and served with *whitenoise*.

Verify health
* https://massibot-graph.azurewebsites.net/docs
* https://massibot.azurewebsites.net

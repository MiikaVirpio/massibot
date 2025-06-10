import os
import azure.functions as func

from bot.api import app as fastapi_app
from web.wsgi import application as django_app


app = func.FunctionApp()

@app.function_name("fastapi")
@app.route("bot/{*route}", auth_level=func.AuthLevel.ANONYMOUS)
async def register_fastapi(req: func.HttpRequest) -> func.HttpResponse:
    return await func.AsgiMiddleware(fastapi_app).handle_async(req)

@app.function_name("django")
@app.route("web/{*route}", auth_level=func.AuthLevel.ANONYMOUS)
def register_django(req: func.HttpRequest) -> func.HttpResponse:
    return func.WsgiMiddleware(django_app).handle(req)

@app.function_name("migrate")
@app.route("/managepy/migrate", methods=["POST"], auth_level=func.AuthLevel.FUNCTION)
def migrate(req: func.HttpRequest) -> func.HttpResponse:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "web.settings")
    from django.core.management import execute_from_command_line
    execute_from_command_line(['manage.py', 'migrate'])
    return func.HttpResponse("Migration complete")

@app.function_name("createsuperuser")
@app.route("/managepy/createsuperuser", methods=["POST"], auth_level=func.AuthLevel.FUNCTION)
def createsuperuser(req: func.HttpRequest) -> func.HttpResponse:
    os.environ["DJANGO_SUPERUSER_PASSWORD"] = req.get_json().get("password")
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "web.settings")
    from django.core.management import execute_from_command_line
    execute_from_command_line(['manage.py', 'createsuperuser', '--noinput', '--email', req.get_json().get("email"), '--username', req.get_json().get("username")])
    return func.HttpResponse(f'User "{req.get_json().get("username")}" created')

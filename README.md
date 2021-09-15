# Django restmote

This package allows to synchronize a local database pulling data from a REST API. To populate the local database, Django ORM is used.

### Populate a local database from a remote one. The database already existed and wasn't build with Django. The script to sync external data is out from the Django project.

First, we need to define our models so restmote can work with them. To do so, Django provides us an awesome management command: `inspectdb`. So, let's build our Django models:

1. Build our project: `django_admin startproject project`
2. `cd project/project` and edit the _settings.py_ file. Set the database variables so you can access it (NAME, BACKEND, PORT, etc.).
3. Once set, execute the `python manage.py inspectdb` command. It will print lots of stuff (your models). If the commands throws an error, check your database variables are correct.
4. If the command worked, create a new application `python manage.py startapp app`.
5. Do `python manage.py inspectdb > app/models.py`

With this, you will have your models defined in your Django app. To check it is working do `python manage.py shell` and then try to import your models with `from app.models import Model1`. You can also check to obtain all the objects with `Model1.objects.all()`.


Having the previous steps, we now need to define some variables in our `project/project/settings.py` file:

* RESTMOTE_HOST: Host where the API REST is serving the data. Ex: 'https://api.github.com/'
* RESTMOTE_PORT: Port where the API REST is serving. Ex: '80'
* RESTMOTE_API_ROOT: Root of the API in the server. Just in case the API ROOT is different from the HOST.
* RESTMOTE_FILTER_FIELD: File to filter data [to improve].
* RESTMOTE_SNAP_FILE: File to store the last filter [we use date filtering now with last_modified field for the content, to improve].


With those variables defined, we can now create a script (anywhere) that will collect data from the external API and save it in our local database:


    import sys
    import django
    import os

    sys.path.append("/path/to/your_project")
    os.environ["DJANGO_SETTINGS_MODULE"] = "project.settings"
    django.setup()
    from contents.models import GithubUser
    from restmote.sync import full_sync


    githubuser_field_bindings = {
        'login': 'field1',
        'avatar_url': 'field2',
    }

   full_sync("/users", "", Model1, githubuser_field_bindings)


With this code we would pull github users to our local database and create new instances with 'field1' and 'field2' columns being the 'login' and the 'avatar_url' respectively (you can change the bindings according to your column models). In most cases the bindings will probably be identical mappings:

```
    githubuser_field_bindings = {
        'login': 'login',
        'avatar_url': 'avatar_url',
    }
```

The additional argument static_field_bindings, provided to either the sync_objects or full_sync functions, is similar to the field_bindings just mentioned. However, it will define static, fixed, fields which are not synced from the remote source.  Rather, you may specify that a certain field should be populated with a certain hardcoded value.

The argument rfilter in the remove_objects function allows you to only remove a certain subset of items. Otherwise, all objects are potentially purged during the removal stage. The purpose of rfilter is to allow storing the results of multiple different syncs in a single table. If each sync and removal applies to a discrete set of objects, and those can be selected/filtered by a simple query filter, then multiple syncs can share a single table. 

It is not necessary to use either static_field_bindings or rfilter. However, when they are used, a common situation would be that those two variables are identical.  Because you mark each set of objects with a certain value when saving them to the database, and that same value is the selector during removal.  

Now you can call this script periodically (using cron) to synchronize your models.  

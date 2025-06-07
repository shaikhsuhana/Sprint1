from django.http import HttpRequest
from django.shortcuts import redirect
from django.contrib import messages


def redirect_autheticated_user(view_func):

    def wrapper(request: HttpRequest, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect("home")
        
        return view_func(request, *args, **kwargs)
    
    return wrapper


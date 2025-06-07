from django.http import HttpRequest
from django.shortcuts import redirect
from django.contrib import messages



def employer_required(view_func):
    def wrapper(request: HttpRequest, *args, **kwargs):
        if not request.user.is_authenticated or request.user.role != 'employer':
            messages.error(request, "Only employers can perform this action.")
            return redirect("home")
        return view_func(request, *args, **kwargs)
    return wrapper

def jobseeker_required(view_func):
    def wrapper(request: HttpRequest, *args, **kwargs):
        if not request.user.is_authenticated or request.user.role != 'jobseeker':
            messages.error(request, "Only jobseekers can perform this action.")
            return redirect("home")
        return view_func(request, *args, **kwargs)
    return wrapper
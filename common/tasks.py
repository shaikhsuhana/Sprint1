from celery import shared_task
from django.core.mail import EmailMultiAlternatives
from django.template.loader import get_template

EMAIL_FROM = "suhanashaikh358@gmail.com"

@shared_task
def send_email(subject: str, email_to: list[str], html_template, context):
    msg = EmailMultiAlternatives(
        subject=subject, from_email=EMAIL_FROM, to=email_to
    )
    html_template = get_template(html_template)
    html_alternative = html_template.render(context)
    print("Rendered Email HTML:\n", html_alternative)  # Debug output to console/logs
    msg.attach_alternative(html_alternative, "text/html")

    msg.send(fail_silently=False)

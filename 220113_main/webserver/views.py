from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, HttpResponseRedirect
from django.template import loader
from django.http import Http404
from .models import ProfileAndPlant, Profile
from django.urls import reverse
from django.views import generic
from django.contrib.auth import login, authenticate, logout
from django.contrib import messages
from .forms import NewUserForm
from django.contrib.auth.forms import AuthenticationForm
from .forms import RegisterForm, LoginForm
from django.views import View
from django.contrib.auth.views import LoginView
from django.contrib.auth.signals import user_logged_out, user_logged_in
from django.urls import reverse_lazy
from django.contrib.auth.views import PasswordResetView
from django.contrib.messages.views import SuccessMessageMixin
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import PasswordChangeView
from django.contrib.messages.views import SuccessMessageMixin
from django.contrib.auth.decorators import user_passes_test
from .forms import UpdateUserForm, UpdateProfileForm, CreatePlantForm
from django.contrib.auth.models import User
import random
import requests 
import os
from dotenv import load_dotenv
from django.http import JsonResponse
import json

class ChangePasswordView(SuccessMessageMixin, PasswordChangeView):
    template_name = 'webserver/change_password.html'
    success_message = "Successfully Changed Your Password"
    success_url = reverse_lazy('home')


@login_required(login_url='webserver:login')
def show_plants(request):
    auth_server_header = _auth_server_header()
    context = {}
    if request.method == 'POST':    
        url_plant_action = 'http://127.0.0.1/api/action/'
        plant_id = 0
        if 'plant_id_activate' in request.POST:
            plant_id = request.POST['plant_id_activate']
            url_plant_action+='on'
            params = {'plant_id':plant_id}
            requests.post(url_plant_action, params=params, headers=auth_server_header)
        elif 'plant_id_deactivate' in request.POST:
            plant_id = request.POST['plant_id_deactivate']
            url_plant_action+='off'
            params = {'plant_id':plant_id}
            requests.post(url_plant_action, params=params, headers=auth_server_header)
        elif 'sell' in request.POST:
            data_transaction = request.POST['sell'].split(',')
            plant_id = data_transaction[0]; sell_amount = data_transaction[1];
            if int(sell_amount) > 0:
                url_plant_action = 'http://127.0.0.1/api/action/sell'
                params = {'plant_id':plant_id,'watt_h':sell_amount}
                requests.post(url_plant_action, params=params, headers=auth_server_header)
        elif 'gen_ticket' in request.POST:
            plant_id = request.POST['gen_ticket']
            #ticket = get_ticket(request, plant_id)
            #data_new_ticket = ticket.content
            return get_ticket_display(request, plant_id)

    if request.user.is_superuser:
        r = requests.get('http://127.0.0.1/api/plants',headers=auth_server_header)
        prosumer_records = r.json()
        return render(request, 'webserver/all_plants.html', context={'data':prosumer_records,'is_admin':1}) 
    
    auth_user = request.user.id
    profile_id = Profile.objects.get(user_id = auth_user).id
    # now fetch all the connected plants to user. 
    all_plant_ids = ProfileAndPlant.objects.filter(user_id_id=profile_id)
    plant_ids = []
    for record in all_plant_ids:
        plant_ids.append(record.plant_id)
    params = {'plant_id': plant_ids}
    r = requests.get('http://127.0.0.1/api/plants', headers=auth_server_header, params=params)
    prosumer_records = r.json()
    stored_charge = 0
    for plant in prosumer_records:
        stored_charge+=plant['stored'] 
    return render(request, 'webserver/all_plants.html', context={'data':prosumer_records, 'is_admin':0, 'stored_charge':stored_charge})
    
def test_activate_deactivate(request):
    auth_server_header = _auth_server_header()
    url = 'http://127.0.0.1/api/action/'
    plant_id = 0
    if 'plant_id_activate' in request.POST:
        plant_id = request.POST['plant_id_activate']
        url = url+'on'
    elif 'plant_id_deactivate' in request.POST:
        plant_id = request.POST['plant_id_deactivate']
        url = url+'off'
    params = {'plant_id':plant_id}
    requests.post(url, params=params, headers=auth_server_header)
    return redirect(request.META['HTTP_REFERER'])



@login_required(login_url='webserver:login')
def weather_conditions(request):
    auth_server_header = _auth_server_header()
    r = requests.get('http://127.0.0.1/api/weather', headers=auth_server_header)
    weather_data = r.json()
    return render(request, 'webserver/weather.html',context={'data':weather_data})

def _auth_server_header():
    load_dotenv()
    header = {'Authorization': os.getenv('AUTH_SECRET_KEY')}
    return header 


#TODO: Find some way to make a nice graph in html/js...
@login_required(login_url='webserver:login')
def price_graph(request):
    auth_server_header = _auth_server_header()
    r = requests.get('http://127.0.0.1/api/price', headers= auth_server_header)
    price_history = r.json()
    date = []; time=[]; price=[]
    for price_record in price_history:
        temp_date,temp_time=price_record['time'].split(',')
        date.append(temp_date);time.append(temp_time)
        price.append(price_record['price'])
    axis = ['Price','Date','Time']
    #if request.user.is_authenticated: #
    #return HttpResponse(r)
    return render(request, 'webserver/price_history.html', context={'price_data': price_history})





def gen_plant_properties(plant_type):
    plant_stats = {'type':plant_type,'storage':0}
    rand_factor = random.random()
    if plant_type=="wind_turbine":
        plant_stats['consumption'] = 5+rand_factor*2  
        plant_stats['production'] = 8+rand_factor*1.5
    elif plant_type=="home_resident":
        plant_stats['consumption'] = 4+rand_factor*2
        plant_stats['production'] = 5+rand_factor*3
    elif plant_type=="nuclear_reactor":
        plant_stats['consumption'] = 40+rand_factor*3
        plant_stats['production'] = 94+rand_factor*2
    elif plant_type=="coal_plant":
        plant_stats['consumption'] = 50+rand_factor*2
        plant_stats['production'] = 79+rand_factor*3
    elif plant_type=="solar_plant":
        plant_stats['consumption'] = 40+rand_factor*2 
        plant_stats['production'] = 50+rand_factor*2
    return plant_stats




@login_required(login_url='webserver:login')
def create_plant_form(request):
    if request.method == 'POST':
        plant_type = request.POST['plant_type']
        params = gen_plant_properties(plant_type)
        auth_server_header = _auth_server_header()
        url = f'http://127.0.0.1/plant_server/create/'
        r = requests.post(url, headers=auth_server_header, params=params)
        if r.status_code != 201:
            return HttpResponse('CREATE PLANT FAILED', status=401)
        # Request was confirmed by plant server.
        # Get user id and update relation db with the newly created plant
        req_data = r.json()
        plant_id = req_data['newly_created_plant']
        auth_user = request.user.id
        profile_id = Profile.objects.get(user_id = auth_user).id
        # update db of created plant
        ProfileAndPlant.objects.create(plant_id=plant_id, plant_type=plant_type, user_id_id=profile_id)
        return HttpResponseRedirect('plants')
    form = CreatePlantForm()
    context = {'form':form}
    return render(request, 'webserver/create_plant.html', context)


@login_required(login_url='webserver:login')
def get_ticket_display(request, plant_id):
    user = request.user.id
    record_profile = Profile.objects.get(user_id = user)
    user_access_to_plant = ProfileAndPlant.objects.filter(user_id=record_profile.id, plant_id=plant_id)
    if not user_access_to_plant:
        return HttpResponse('Unauthorized', status = 401)
    auth_server_header = _auth_server_header()
    url= f'http://127.0.0.1/api/ticket/create'
    params = {'plant_id':plant_id}
    request_ticket = requests.get(url, params=params, headers=auth_server_header)
    if request_ticket.status_code!=200:
        return HttpResponse('Unauthorized', status=401)
    data = request_ticket.json()
    context = {'ticket':data['new_ticket'], 'plant_id':plant_id}
    return render(request,'webserver/ticket.html', context)

@login_required(login_url='webserver:login')
def get_ticket(request, plant_id):
    # request.user.id <- profile.user_id <- profileandplants.user_id_id (points to the profile.id)
    user = request.user.id
    record_profile = Profile.objects.get(user_id = user)
    user_access_to_plant = ProfileAndPlant.objects.filter(user_id=record_profile.id, plant_id=plant_id)
    if not user_access_to_plant:
        return HttpResponse('Unauthorized', status = 401)
    auth_server_header = _auth_server_header()
    url= f'http://127.0.0.1/api/ticket/create'
    params = {'plant_id':plant_id}
    request_ticket = requests.get(url, params=params, headers=auth_server_header)
    if request_ticket.status_code!=200:
        return HttpResponse('Unauthorized', status=401)
    return HttpResponse(request_ticket)



@login_required(login_url='webserver:login')
def admin_delete_user(request,user_id):
    if not request.user.is_superuser:
        return HttpResponse('Unauthorized', status=401)
    #Simply delete user, and return 204, as we do not care if the user would not exist.
    user_to_delete = User.objects.filter(id=user_id)
    user_to_delete.delete()
    return HttpResponse('admin_delete_user_COMPLETE BUT CHANGE RESPONSE.') # Change to delete user, read model and then delete that sucker.

@login_required(login_url='webserver:login')
def admin_delete_plant(request,plant_id):
    if not request.user.is_superuser: #or not request.POST: #Django apparantly dislikes delete methods...cheeze...
        return HttpResponse('Unauthorized', status=401)
    # Delete all instances of plant_id in plant server.
    url = f'http://127.0.0.1/api/del/plant/'
    params = {'plant_id': plant_id} #As we see its actually a get.
    auth_server_header = _auth_server_header()
    request_deletion = requests.delete(url, params=params, headers=auth_server_header)
    if request_deletion.status_code != 204:
        return HttpResponse('Unauthorized', status=401)
    all_records = ProfileAndPlant.objects.filter(plant_id=plant_id)
    all_records.delete()
    # All went aok, now simp return the fucker, 204,
    return HttpResponse('SUCCESS', status=204)


def check_username_status(request):
    user_list = Profile.objects.order_by('-is_logged_in')
    dict = {}
    ulist = []
    for i in user_list:
        ulist.append({'User_ID':i.user_id, 'Logged_in':i.is_logged_in})
    context = {'users':ulist}
    return render(request, 'webserver/users.html', context)


@login_required(login_url='webserver:login')
def profile(request):
    if request.method == 'POST':
        user_form = UpdateUserForm(request.POST, instance=request.user)
        profile_form = UpdateProfileForm(
            request.POST, request.FILES, instance=request.user.profile)

        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, 'Your profile is updated successfully')
            return redirect("webserver:profile")
    else:
        user_form = UpdateUserForm(instance=request.user)
        profile_form = UpdateProfileForm(instance=request.user.profile)

    return render(request, 'webserver/profile.html', {'user_form': user_form, 'profile_form': profile_form})


class ResetPasswordView(SuccessMessageMixin, PasswordResetView):
    template_name = 'webserver/password_reset.html'
    email_template_name = 'webserver/password_reset_email.html'
    subject_template_name = 'webserver/password_reset_subject'
    success_message = "We've emailed you instructions for setting your password, " \
                      "if an account exists with the email you entered. You should receive them shortly." \
                      " If you don't receive an email, " \
                      "please make sure you've entered the address you registered with, and check your spam folder."
    success_url = reverse_lazy('home')


def home(request):
    IndexView(request)

# Class based view that extends from the built in login view to add a remember me functionality


class CustomLoginView(LoginView):
    form_class = LoginForm
    

    def form_valid(self, form):
        remember_me = form.cleaned_data.get('remember_me')
        logged_status = form.cleaned_data.get('is_logged_in')
        if not remember_me:
            # set session expiry to 0 seconds. So it will automatically close the session after the browser is closed.
            self.request.session.set_expiry(0)

            # Set session as modified to force data updates/cookie to be saved.
            self.request.session.modified = True

        # else browser session will be as long as the session cookie time "SESSION_COOKIE_AGE" defined in settings.py
        
        logged_status = True
        return super(CustomLoginView, self).form_valid(form)

def user_logging_in(sender, user, **kwargs):
    record_profile = Profile.objects.get(user_id = user.id)
    record_profile.is_logged_in = True
    record_profile.save(update_fields=['is_logged_in'])

user_logged_in.connect(user_logging_in)

def user_logging_out(sender, user, **kwargs):
    record_profile = Profile.objects.get(user_id = user.id)
    record_profile.is_logged_in = False
    record_profile.save(update_fields=['is_logged_in'])

user_logged_out.connect(user_logging_out)

class RegisterView(View):
    form_class = RegisterForm
    initial = {'key': 'value'}
    template_name = 'webserver/register.html'

    def dispatch(self, request, *args, **kwargs):
        # will redirect to the home page if a user tries to access the register page while logged in
        if request.user.is_authenticated:
            return redirect("webserver:index")

        # else process dispatch as it otherwise normally would
        return super(RegisterView, self).dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        form = self.form_class(initial=self.initial)
        return render(request, self.template_name, {'form': form})

    def post(self, request, *args, **kwargs):
        form = self.form_class(request.POST)

        if form.is_valid():
            form.save()

            username = form.cleaned_data.get('username')
            messages.success(request, f'Account created for {username}')

            return redirect("webserver:index")

        return render(request, self.template_name, {'form': form})



class IndexView(generic.ListView):
    template_name = 'webserver/index.html'
    context_object_name = 'latest_question_list'

    def get_queryset(self):
        """Return the last five published questions."""
        



# Testing call to connect auth/django apps to plant_server.



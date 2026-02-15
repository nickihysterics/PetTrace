from django.urls import path

from .cabinets import (
    documents_board,
    finance_board,
    hospitalization_board,
    mar_board,
    role_cabinet_detail,
    role_cabinets_index,
)
from .home import role_home_detail, role_home_redirect
from .views import (
    FrontendLoginView,
    FrontendLogoutView,
    appointment_create,
    appointments_board,
    dashboard,
    labs_board,
    owner_create,
    owners_list,
    pet_create,
    pets_list,
    root_redirect,
    visit_detail,
)

app_name = "frontend"

urlpatterns = [
    path("", root_redirect, name="root"),
    path("login/", FrontendLoginView.as_view(), name="login"),
    path("logout/", FrontendLogoutView.as_view(), name="logout"),
    path("home/", role_home_redirect, name="role-home"),
    path("home/<slug:role_key>/", role_home_detail, name="role-home-detail"),
    path("dashboard/", dashboard, name="dashboard"),
    path("owners/", owners_list, name="owners-list"),
    path("owners/new/", owner_create, name="owner-create"),
    path("pets/", pets_list, name="pets-list"),
    path("pets/new/", pet_create, name="pet-create"),
    path("appointments/", appointments_board, name="appointments-board"),
    path("appointments/new/", appointment_create, name="appointment-create"),
    path("visits/<int:visit_id>/", visit_detail, name="visit-detail"),
    path("labs/", labs_board, name="labs-board"),
    path("cabinets/", role_cabinets_index, name="role-cabinets"),
    path("cabinets/<slug:role_key>/", role_cabinet_detail, name="role-cabinet-detail"),
    path("documents/", documents_board, name="documents-board"),
    path("hospitalization/", hospitalization_board, name="hospitalization-board"),
    path("mar/", mar_board, name="mar-board"),
    path("finance/", finance_board, name="finance-board"),
]

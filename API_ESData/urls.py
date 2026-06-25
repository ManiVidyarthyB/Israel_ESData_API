"""API_ESData URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.11/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import path, include
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.urls import path, include
# from django.contrib import admin
from django.contrib.auth.models import User
from rest_framework import routers, serializers, viewsets
from . import views

# Serializers define the API representation.
class UserSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = User
        fields = ('url', 'username', 'email', 'is_staff')

# ViewSets define the view behavior.
class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer

# Routers provide an easy way of automatically determining the URL conf.
router = routers.DefaultRouter()
router.register(r'users', UserViewSet)

# Wire up our API using automatic URL routing.
# Additionally, we include login URLs for the browsable API.

urlpatterns = [
    path('', include(router.urls)),

    path('get_all/', views.GetAll.as_view()),

    path('get_player/', views.GetPlayer.as_view()),

    # Get Display_pics
    path('get_pics/', views.GetDisplayPics.as_view()),
    path('get_display_pics/', views.GetDisplayPics.as_view()),
    path('get_project_display_pics/', views.GetProjectDisplayPics.as_view()),
    path('get_pics_with_height/', views.GetDisplayPicsWithCustomHeight.as_view()),
    path('get_vehicle_attributes/', views.GetProjectVehicleInfo.as_view()),
    path('get_detail_pics/', views.GetDetailPics.as_view()),
    path('get_pics_player/', views.GetPicsPlayer.as_view()),

    path('get_interior/', views.GetInterior.as_view()),
    path('get_interior360/', views.GetInterior.as_view()),

    path('get_exterior360/', views.GetExterior.as_view()),

    path('get_videos/', views.GetVideos.as_view()),
    path('api-auth/', include('rest_framework.urls')),

    path('get_thumbnail_pics/', views.GetThumbnailPics.as_view()),
    path('get_thumbnail_pics_test/', views.GetThumbnailPicsTest.as_view()),

    path('Jidd/2242175545/get_display_pics/', views.GetDisplayPics.as_view()),
    path('Jidd/2242175545/get_player/', views.GetPlayer.as_view()),
    path('Jidd/2242175545/get_exterior360/', views.GetExterior.as_view()),
    path('Jidd/2242175545/get_detail_pics/', views.GetDetailPics.as_view()),
    path('Jidd/2242175545/get_interior360/', views.GetInterior.as_view()),

    path('get_bgred_pics/', views.GetBGREDPics.as_view()),
]

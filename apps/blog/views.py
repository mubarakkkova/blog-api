from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from apps.blog.models import Category, Comment, Post, Tag
from apps.blog.serializers import (
    CategorySerializer,
    CommentSerializer,
    PostSerializer,
    TagSerializer,
)


class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes=(IsAuthenticated,)

class TagViewSet(viewsets.ModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes =(IsAuthenticated,)


class PostViewSet(viewsets.ModelViewSet):
    queryset = Post.objects.all()
    serializer_class = PostSerializer
    permission_classes=(IsAuthenticated,)


class CommentViewSet(viewsets.ModelViewSet):
    queryset = Comment.objects.all()
    serializer_class = CommentSerializer
    permission_classes=(IsAuthenticated,)

    
        
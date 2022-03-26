from flask import Blueprint, request, redirect, url_for, make_response, jsonify
from flask_jwt_extended import create_access_token, create_refresh_token
from flask_apispec import use_kwargs, marshal_with
from marshmallow import fields
from blog.models import User, Article, Comment, Tag, ArticleSchema, Follow
from flask_login import login_user, logout_user, login_required, current_user
from blog.estensions import db
from slugify import slugify
import json

articles_bp = Blueprint('articles', __name__)


# 为了避免不同查询条件写多个视图， 使用flask_apispec提供的@use_kwargs装饰器
@articles_bp.route('/api/articles', methods=['GET'])
@use_kwargs({'tag': fields.Str(), 'author': fields.Str(), 'favorited': fields.Str(), 'limit': fields.Int(),
             'offset': fields.Int()})
@marshal_with(ArticleSchema)
def articles_show(tag=None, author=None, favorited=None, limit=20, offset=0):
    res = Article.query
    if tag:
        res = res.filter(Article.tags.any(Tag.name == tag))
    if author:
        res = res.join(Article.author).join(User).filter(User.username == author)
    if favorited:
        res = res.join(Article.collectors).filter(User.username == favorited)
    return res.all()


# 返回关注的用户创建的多篇文章
@articles_bp.route('/api/articles/feed', methods=['GET'])
@login_required
@use_kwargs({'limit': fields.Int(), 'offset': fields.Int()})
@marshal_with(ArticleSchema)
def articles_feed(limit=20, offset=0):
    if current_user.is_authenticated:
        target_articles = Article.query.join(Follow, Follow.followed_id == Article.author_id).filter(
            Follow.follower_id == current_user.id).order_by(Article.create_time).offset(offset).limit(limit).all()
        ret_data = {
            "code": 10000,
            "articles": target_articles,
            "message": "null"
        }
        return jsonify(ret_data)


# 获取单篇文章
@articles_bp.route('/api/articles/<slug>', methods=['GET'])
@use_kwargs({'slug': fields.Str()})
def article_get(slug):
    target_article = Article.query.filter(Article.slug == slug).first()
    if target_article is not None:
        ret_data = {
            "code": 10000,
            "articles": target_article,
            "message": "null"}
        return jsonify(ret_data)
    else:
        ret_data = {
            "code": 10004,
            "errors": {
                "body": [
                    "can't be empty"
                ]
            },
            "message": "no article"
        }
        return jsonify(ret_data)


# 创作文章
@articles_bp.route('/api/articles', methods=['POST'])
@login_required
def article_create():
    data = json.loads(request.get_data())
    dic1 = data.get('article')
    title = dic1['title']
    description = dic1['description']
    body = dic1['body']
    if current_user.is_authenticated:
        exist_article = Article.query.filter_by(title=title).first()
        if exist_article is not None:
            ret_data = {
                "code": 10005,
                "body": "该文章已存在！",
                "message": "null"
            }
            return jsonify(ret_data)
        article = Article()
        article.title = title
        article.author = current_user
        article.description = description
        article.body = body
        article.slug = slugify(title)
        for tag in dic1["tagList"]:
            article.tags.append(tag)
        db.session.add(article)
        db.session.commit()
        ret_data = {
                "code": 10000,
                "articles": {
                    "title": article.title,
                    "description": article.description,
                    "body": article.body,
                    "tagList": article.tags,
                },
                "message": "null"
            }
        return jsonify(ret_data)

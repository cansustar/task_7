from flask import Blueprint, request, jsonify
from flask_apispec import use_kwargs, marshal_with
from marshmallow import fields
from blog.models import User, Article, Comment, Tag, Collect, article_schema, articles_schema, comment_schema, \
    comments_schema, Follow
from flask_login import login_required, current_user
from blog.estensions import db
from slugify import slugify
import json

articles_bp = Blueprint('articles', __name__)


# 为了避免不同查询条件写多个视图， 使用flask_apispec提供的@use_kwargs装饰器
@articles_bp.route('/api/articles', methods=['GET'])
@marshal_with(articles_schema)
def articles_show(limit=20, offset=0):
    tag = request.args.get('tag')
    author = request.args.get('author')
    username = request.args.get('favorited')
    if tag is not None:
        res = Article.query.filter(Article.tagList.any(Tag.name == tag))
        return res.offset(offset).limit(limit).all()
    if author is not None:
        target_author = User.query.filter(User.username == author).first()
        res = Article.query.filter(Article.author == target_author)
        return res.offset(offset).limit(limit).all()
    if username is not None:
        # 要想从user的collection中返回响应，遇到的问题是从collection中获取的响应与响应模型不一致
        # join的用法
        # 这里获得的是所有Collect模型的响应，而不是Article响应模型
        res = Article.query.join(Article.collectors).filter(User.username == username)
        return res.offset(offset).limit(limit).all()
    else:
        return Article.query.offset(offset).limit(limit).all()


# 返回关注的用户创建的多篇文章
@articles_bp.route('/api/articles/feed', methods=['GET'])
@login_required
@use_kwargs({'limit': fields.Int(), 'offset': fields.Int()})
@marshal_with(articles_schema)
def articles_feed(limit=20, offset=0):
    if current_user.is_authenticated:
        target_articles = Article.query.join(Follow, Follow.followed_id == Article.author_id).filter(
            Follow.follower_id == current_user.id).order_by(Article.createdAt).offset(offset).limit(limit).all()
        return target_articles


# 获取单篇文章
@articles_bp.route('/api/articles/<slug>', methods=['GET'])
@use_kwargs({'slug': fields.Str()})
@marshal_with(article_schema)
def article_get(slug):
    target_article = Article.query.filter(Article.slug == slug).first()
    if target_article is not None:
        if request.method == 'GET':
            return target_article
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
@marshal_with(article_schema)
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
        # 对于多对多关系 要添加的标签必须已有该实例，所以对于新标签要先创建该实例，再添加 否则报错 'str' object has no attribute '_sa...'
        for tag in dic1["tagList"]:
            exist_tag = Tag.query.filter_by(name=tag).first()
            if exist_tag is None:
                new_tag = Tag()
                new_tag.name = tag
                db.session.add(new_tag)
                db.session.commit()
                article.tagList.append(new_tag)
            if exist_tag is not None:
                article.tagList.append(exist_tag)
        db.session.add(article)
        db.session.commit()
        return article


# 更新文章
@articles_bp.route('/api/articles/<slug>', methods=['PUT'])
@login_required
@marshal_with(article_schema)
def article_update(slug):
    target_article = Article.query.filter(Article.slug == slug).first()
    if target_article is None:
        ret_data = {"code": 10004,
                    "errors": {
                        "body": [
                            "can't be empty"
                        ]
                    },
                    "message": "no article"
                    }
        return jsonify(ret_data)
    # 判断要操作的文章的作者是否为当前用户
    if target_article.author == current_user:
        data = json.loads(request.get_data())
        # 使用get方法获取value，如果没有key的话返回None，而如果在不知道有无要的key的情况下直接data['']的方式获取，则会报错无该key
        title = data['article'].get('title')
        description = data['article'].get('description')
        body = data['article'].get('body')
        if title is not None:
            target_article.title = title
            target_article.slug = slugify(title)
        if description is not None:
            target_article.description = description
        if body is not None:
            target_article.body = body
        db.session.add(target_article)
        # 报错一次 问题在于当我想要测试是否能够验证当前用户为目标文章作者时，
        # 创建新文章后在update请求里没有把请求的json数据中的title属性值修改，导致unique的slug冲突，在提交时报错
        db.session.commit()
        return target_article
    else:
        ret_data = {"code": 10006,
                    "errors": {
                        "body": [
                            "can't be empty"
                        ]
                    },
                    "message": "not author"
                    }
        return jsonify(ret_data)


# 删除文章
@articles_bp.route('/api/articles/<slug>', methods=['DELETE'])
@login_required
def article_delete(slug):
    target_article = Article.query.filter(Article.slug == slug).first()
    if target_article is None:
        ret_data = {"code": 10004,
                    "errors": {
                        "body": [
                            "can't be empty"
                        ]
                    },
                    "message": "no article"
                    }
        return jsonify(ret_data)
    # 判断要操作的文章的作者是否为当前用户
    if target_article.author == current_user:
        db.session.delete(target_article)
        db.session.commit()
        ret_data = {"code": 10000,
                    "errors": {
                        "body": [
                            "can't be empty"
                        ]
                    },
                    "message": "success"
                    }
        return jsonify(ret_data)

    else:
        ret_data = {"code": 10006,
                    "errors": {
                        "body": [
                            "can't be empty"
                        ]
                    },
                    "message": "not author"
                    }
        return jsonify(ret_data)


# 向文章添加评论
@articles_bp.route('/api/articles/<slug>/comments', methods=['POST'])
@login_required
@use_kwargs(comment_schema)
@marshal_with(comment_schema)
def article_comment(slug):
    target_article = Article.query.filter(Article.slug == slug).first()
    if target_article is None:
        ret_data = {"code": 10004,
                    "errors": {
                        "body": [
                            "can't be empty"
                        ]
                    },
                    "message": "no article"
                    }
        return jsonify(ret_data)
    data = json.loads(request.get_data())
    comment_body = data['comment'].get('body')
    comment = Comment()
    comment.body = comment_body
    comment.author = current_user
    comment.article = target_article
    db.session.add(comment)
    db.session.commit()
    return comment


# 返回多条评论
@articles_bp.route('/api/articles/<slug>/comments', methods=['GET'])
@login_required
@marshal_with(comments_schema)
def get_comments(slug):
    target_article = Article.query.filter(Article.slug == slug).first()
    if target_article is None:
        ret_data = {"code": 10004,
                    "errors": {
                        "body": [
                            "can't be empty"
                        ]
                    },
                    "message": "no article"
                    }
        return jsonify(ret_data)
    return target_article.comments


# 删除评论
@articles_bp.route('/api/articles/<slug>/comments/<id>', methods=['DELETE'])
@login_required
def delete_comment(slug, id):
    target_article = Article.query.filter(Article.slug == slug).first()
    if target_article is None:
        ret_data = {"code": 10004,
                    "errors": {
                        "body": [
                            "can't be empty"
                        ]
                    },
                    "message": "no article"
                    }
        return jsonify(ret_data)
    # 在查询要删除的评论时报错AttributeError: 'InstrumentedList' object has no attribute 'filter_by'
    # 原因是没有在article模型类中为comments字段设置lazy='dynamic'
    target_comment = target_article.comments.filter_by(id=id, author=current_user).first()
    if target_comment is None:
        ret_data = {"code": 10004,
                    "errors": {
                        "body": [
                            "can't be empty"
                        ]
                    },
                    "message": "no comment"
                    }
        return jsonify(ret_data)
    db.session.delete(target_comment)
    db.session.commit()
    ret_data = {"code": 10000,
                "errors": {
                    "body": [
                        "can't be empty"
                    ]
                },
                "message": "success"
                }
    return jsonify(ret_data)


# 喜欢文章
@articles_bp.route('/api/articles/<slug>/favorite', methods=['POST'])
@login_required
@marshal_with(article_schema)
def favorite_article(slug):
    target_article = Article.query.filter(Article.slug == slug).first()
    if target_article is None:
        ret_data = {"code": 10004,
                    "errors": {
                        "body": [
                            "can't be empty"
                        ]
                    },
                    "message": "no article"
                    }
        return jsonify(ret_data)
    current_user.collect(target_article)
    return target_article


# 取消喜欢文章
@articles_bp.route('/api/articles/<slug>/favorite', methods=['DELETE'])
@login_required
@marshal_with(article_schema)
def unfavorite_article(slug):
    target_article = Article.query.filter(Article.slug == slug).first()
    if target_article is None:
        ret_data = {"code": 10004,
                    "errors": {
                        "body": [
                            "fail"
                        ]
                    },
                    "message": "no article"
                    }
        return jsonify(ret_data)
    current_user.uncollect(target_article)
    return target_article


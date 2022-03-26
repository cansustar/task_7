from blog.estensions import db
from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from marshmallow import Schema
from slugify import slugify

# 标签与文章的多对多关系的关联表
tagging = db.Table('tagging',
                   db.Column('article_id', db.Integer, db.ForeignKey('article.id')),
                   db.Column('tag_id', db.Integer, db.ForeignKey('tag.id'))
                   )


# 收藏文章 一个用户可以收藏多篇文章， 一篇文章也可以被多个用户收藏，
# article模型与user模型也需要建立多对多关系，
# 使用关系模型来将article和user的多对多关系分离成User模型和Collect模型的一对多关系，以及Article模型和Collect模型的一对多关系
class Collect(db.Model):
    collector_id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)
    collected_id = db.Column(db.Integer, db.ForeignKey('article.id'), primary_key=True)
    # 存储收藏动作发生的时间
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    # 与User，Article模型的关系属性
    collector = db.relationship('User', back_populates='collections', lazy='joined')
    collected = db.relationship('Article', back_populates='collectors', lazy='joined')


class Article(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(60))
    slug = db.Column(db.Text, unique=True)
    description = db.Column(db.String(60))
    body = db.Column(db.Text)
    # 与tag模型的关系属性
    tags = db.relationship('Tag', secondary=tagging, back_populates='articles')
    author = db.relationship('User', back_populates='articles')
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    create_time = db.Column(db.DateTime, default=datetime.utcnow)
    update_time = db.Column(db.DateTime, default=datetime.utcnow)
    # 为文章添加评论字段时，与评论数据库定义关系属性，并设置backref参数指向文章实例，\
    # 使得可以通过评论获取到文章，同时设置cascade参数为all，设置级联删除，在删除文章时不用手动删除对应的评论。
    comments = db.relationship('Comment', back_populates='article', cascade='all')
    # 与Collect模型的关系属性
    collectors = db.relationship('Collect', back_populates='collected', cascade='all')


class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.Text)
    author = db.Column(db.ForeignKey('user.id'))
    create_time = db.Column(db.DateTime, default=datetime.utcnow)
    upgrade_time = db.Column(db.DateTime, default=datetime.utcnow)
    article = db.relationship('Article', back_populates='comments')
    article_id = db.Column(db.Integer, db.ForeignKey('article.id'))


class Tag(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(20), unique=True, index=True)
    articles = db.relationship('Article', secondary=tagging, back_populates='tags')


# 实现关注功能
class Follow(db.Model):
    follower_id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)
    followed_id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)
    follower = db.relationship('User', foreign_keys=[follower_id], back_populates='following', lazy='joined')
    followed = db.relationship('User', foreign_keys=[followed_id], back_populates='followers', lazy='joined')


# 为了设置自引用关系，user模型需要在follow后定义
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(36), unique=True, index=True)
    email = db.Column(db.String(254), unique=True, index=True)
    password_hash = db.Column(db.String(128))
    bio = db.Column(db.String(70))
    image = db.Column(db.String(70))
    confirmed = db.Column(db.Boolean, default=False)
    token = db.Column(db.String(254))
    articles = db.relationship('Article', back_populates='author', cascade='all')
    # 与Collect模型的关系属性
    collections = db.relationship('Collect', back_populates='collector', cascade='all')
    # following 为自己的关注对象
    following = db.relationship('Follow', foreign_keys=[Follow.follower_id], back_populates='follower',
                                lazy='dynamic', cascade='all')
    # followers 为自己的粉丝
    followers = db.relationship('Follow', foreign_keys=[Follow.followed_id], back_populates='followed',
                                lazy='dynamic', cascade='all')

    # set_password()函数用来设置密码，接收密码原始值作为参数，将密码的散列值设为password_hash的只
    @property
    def password(self):
        raise AttributeError('密码不可读！')

    # validate_password（）函数用来验证密码是否和对应的散列值相符，传入散列值(自动传入)与password（手动传入原始值），返回布尔值
    @password.setter
    def password(self, password):
        # 这样就能直接user.password=password来设置密码，
        # 并且设定这个属性的值时，赋值方法会调用generate_password_hash()函数，并把得到的散列值赋值给password_hash字段
        # 当尝试读取password属性值时，就会返回错误
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)

    # 关注
    def follow(self, user):
        if not self.is_following(user):
            follow = Follow(follower=self, followed=user)
            db.session.add(follow)
            db.session.commit()

    # 取消关注
    def unfollow(self, user):
        follow = self.following.filter_by(followed_id=user.id).first()
        if follow:
            db.session.delete(follow)
            db.session.commit()

    # 确认是否关注了对方
    def is_following(self, user):
        return self.following.filter_by(followed_id=user.id).first() is not None

    # 确认对方是否是你的粉丝 （自己是否被关注）
    def is_followed_by(self, user):
        return self.followers.filter_by(follower_id=user.id).first() is not None

    # 收藏文章
    def collect(self, article):
        if not self.is_collecting(article):
            collect = Collect(collector=self, collected=article)
            db.session.add(collect)
            db.session.commit()

    # 取消收藏
    def uncollect(self, article):
        collect = self.collected.filter_by(collected_id=article.id).first()
        if collect:
            db.session.delete(collect)
            db.session.commit()

    # 确认是否已收藏该文章
    def is_collecting(self, article):
        return self.collected.filter_by(collected_id=article.id).first() is not None


# 为了一次返回查询的文章列表，以及所要求返回的字段，
# 使用python自带的marshmallow包的Schema类创建一个响应模型
class ArticleSchema(Schema):
    class Meta:
        # 指定返回响应的数据字段
        fields = (
            'slug', 'title', 'description', 'body', 'tagList', 'createdAt', 'updatedAt', 'favorited', 'favoritesCount',
            'author')


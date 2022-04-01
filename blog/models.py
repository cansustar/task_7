from blog.estensions import db
from datetime import datetime
from flask_login import UserMixin, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from marshmallow import Schema, fields, pre_load, post_dump

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
    tagList = db.relationship('Tag', secondary=tagging, back_populates='articles')
    author = db.relationship('User', back_populates='articles')
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    createdAt = db.Column(db.DateTime, default=datetime.utcnow)
    updatedAt = db.Column(db.DateTime, default=datetime.utcnow)
    # 为文章添加评论字段时，与评论数据库定义关系属性，并设置backref参数指向文章实例，\
    # 使得可以通过评论获取到文章，同时设置cascade参数为all，设置级联删除，在删除文章时不用手动删除对应的评论。
    comments = db.relationship('Comment', back_populates='article', cascade='all', lazy='dynamic')
    # 与Collect模型的关系属性
    collectors = db.relationship('Collect', back_populates='collected', cascade='all')


class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.Text)
    author = db.relationship('User', back_populates='comments')
    createAt = db.Column(db.DateTime, default=datetime.utcnow)
    updatedAt = db.Column(db.DateTime, default=datetime.utcnow)
    article = db.relationship('Article', back_populates='comments')
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    article_id = db.Column(db.Integer, db.ForeignKey('article.id'))


class Tag(db.Model):
    # 如果不加这个函数的话，在文章中显示出的tag为 tag1,tag2而不是他们的名称

    def __repr__(self):
        return self.name

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(20), unique=True, index=True)
    articles = db.relationship('Article', secondary=tagging, back_populates='tagList')


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
    comments = db.relationship('Comment', back_populates='author', cascade='all')
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
    @property
    def followed_articles(self):
        return Article.query.join(Follow, Follow.followed_id == Article.author_id).filter(Follow.follower_id == self.id)

    def collect(self, article):
        if not self.is_collecting(article):
            collect = Collect(collector=self, collected=article)
            db.session.add(collect)
            db.session.commit()

    # 取消收藏
    def uncollect(self, article):
        collect = Collect.query.with_parent(self).filter_by(collected_id=article.id).first()
        if collect:
            db.session.delete(collect)
            db.session.commit()

    # 确认是否已收藏该文章
    def is_collecting(self, article):
        return Collect.query.with_parent(self).filter_by(collected_id=article.id).first() is not None


# 返回用户的响应模型
class ProfileSchema(Schema):
    username = fields.Str()
    email = fields.Email()
    password = fields.Str(load_only=True)
    bio = fields.Str()
    image = fields.Url()

    # 测试时发现响应模型中的following返回数据有误，直接使用响应模型返回的following结果都为True
    # 这里先将following字段放到装饰器里另外输出
    # following = fields.Boolean()
    # profile = fields.Nested('self', exclude=('profile',), default=True, load_only=True)

    # @pre_load装饰器的作用
    # def make_user(self, data, **kwargs):
    #    return data['profile']

    @post_dump
    def dump_user(self, data, **kwargs):
        data['following'] = current_user.is_following(User.query.filter(User.email == data['email']).first())
        return data

    class Meta:
        strict = True


profile_schema = ProfileSchema()
profile_schemas = ProfileSchema(many=True)


# 为了一次返回查询的文章列表，以及所要求返回的字段，
# 使用python自带的marshmallow包的Schema类创建一个响应模型
class ArticleSchema(Schema):
    slug = fields.Str()
    title = fields.Str()
    description = fields.Str()
    createdAt = fields.DateTime()
    body = fields.Str()
    # dump_only属性为是否为序列化阶段才使用当前字段，即提交时
    updatedAt = fields.DateTime(dump_only=True)
    # Nestd为外键类型
    author = fields.Nested(ProfileSchema)
    article = fields.Nested("self", exclude=('article',), default=True, load_only=True)
    tagList = fields.List(fields.Str())
    favoritesCount = fields.Int(dump_only=True)
    favorited = fields.Bool(dump_only=True)

    @pre_load
    def make_article(self, data, **kwargs):
        return data['article']

    @post_dump
    def dump_article(self, data, **kwargs):
        # 由于我把收藏文章的方法写给了user，所以这里只能把favorited响应字段写在额外的响应内容里
        data['favorited'] = current_user.is_collecting(Article.query.filter_by(slug=data['slug']).first())
        data['favoritedCount'] = len(Article.query.filter_by(slug=data['slug']).first().collectors)
        return {'article': data}

    @post_dump
    def dump_message(self, data, **kwargs):
        data['message'] = 'success'
        data['code'] = 10000
        data['body'] = 'null'
        return data

    class Meta:
        strict = True


class ArticleSchemas(ArticleSchema):

    @post_dump(pass_many=True)
    def dump_articles(self, data, many, **kwargs):
        return {'articles': data, 'articleCount': len(data)}


# 评论的响应模型
class CommentSchema(Schema):
    createAt = fields.DateTime()
    body = fields.Str()
    updateAt = fields.DateTime(dump_only=True)
    author = fields.Nested(ProfileSchema)
    id = fields.Int()
    comment = fields.Nested('self', exclude=('comment',), default=True, load_only=True)

    @pre_load
    def make_comment(self, data, **kwargs):
        return data['comment']

    @post_dump
    def dump_comment(self, data, **kwargs):
        data['author'] = data['author']
        return {'comment': data}

    @post_dump
    def dump_message(self, data, **kwargs):
        data['message'] = 'success'
        data['code'] = 10000
        data['body'] = 'null'
        return data

    class Meta:
        strict = True


class CommentsSchema(CommentSchema):

    @post_dump
    def dump_comment(self, data, **kwargs):
        data['author'] = data['author']
        return data

    @post_dump(pass_many=True)
    def make_comment(self, data, many, **kwargs):
        return {'comments': data}


article_schema = ArticleSchema()
articles_schema = ArticleSchemas(many=True)
comment_schema = CommentSchema()
comments_schema = CommentsSchema(many=True)

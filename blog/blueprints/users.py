from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, create_refresh_token
from blog.models import User
from flask_login import login_user, logout_user, login_required, current_user
from blog.estensions import db
import json
from blog.utils import validate_token

users_bp = Blueprint('users', __name__)


# 注册
# POST方法，下面获取json串中数据的方法为通用方法，
@users_bp.route('/api/users', methods=['POST', ])
def user_reg():
    # 从请求中获取json数据并解析到字典中
    data = json.loads(request.get_data())
    # 从解析后的字典中获取key为user的数据，并存放到字典中
    dic1 = data.get("user")
    # 判断数据库中是否有该Email（该用户是否已经注册）
    exist_user = User.query.filter(User.email == dic1['email']).first()
    # 如果没有注册，则将新用户保存到数据库中
    if exist_user is None:
        user = User()
        user.email = dic1['email'].lower()
        user.username = dic1['username']
        user.password = dic1['password']
        db.session.add(user)
        db.session.commit()
        ret_data = {
            "code": 10000,
            "data": {"user": {
                "email": user.email,
                "token": user.token,
                "username": user.username,
                "bio": user.bio,
                "image": user.image,

            }
            },
            "message": "success",
            "body": "返回当前用户"
        }

        return jsonify(ret_data)
    # 如果数据库中已有该用户的信息，则返回10001，表示已注册
    else:
        ret_data = {
            "code": 10001,
            "errors": {
                "body": [
                    "当前用户已注册"
                ]
            },
            "message": "fail"
        }
        return jsonify(ret_data)


# 登录
@users_bp.route('/api/users/login', methods=['POST'])
def user_login():
    # 从请求的json串中获取参数email和password
    # 使用request.get_json()获得的数据与json.loads(request.get_data())不同
    data = request.get_json()
    dic1 = data.get("user")
    email = dic1['email']
    password = dic1['password']
    # 现在只查询第一条记录，目的是确认数据库中有现存记录
    exist_user = User.query.filter(User.email == dic1['email']).first()
    # 验证是否已注册：
    if exist_user is None:
        ret_data = {
            "code": 10002,
            "errors": {
                "body": [
                    "输入的邮件地址未注册"
                ]
            },
            "message": "fail"
        }
        return jsonify(ret_data)
    else:
        # 验证邮件地址与密码与数据库中是否一致
        if email == exist_user.email and exist_user.verify_password(password):
            login_user(exist_user)
            # 生成token
            token = create_access_token(identity=exist_user.username)
            exist_user.token = token
            ret_data = {
                "code": 10000,
                'data': {"user": {
                    "email": exist_user.email,
                    "token": exist_user.token,
                    "username": exist_user.username,
                    "bio": exist_user.bio,
                    "image": exist_user.image,

                },
                },
                "message": "success",
                "body": "成功登录"
            }
            return jsonify(ret_data)
        else:
            ret_data = {
                "code": 10009,
                "body": "密码或邮箱错误",
                "message": "fail"
            }
            return jsonify(ret_data)


# 获取当前用户
@users_bp.route('/api/user', methods=['GET'])
def get_current_user():
    if current_user.is_authenticated:
        ret_data = {
            "code": 10000,
            "data": {"user": {
                "email": current_user.email,
                "token": current_user.token,
                "username": current_user.username,
                "bio": current_user.bio,
                "image": current_user.image,

            }},
            "message": "success",
            "body": "成功获取当前用户"
        }

        return jsonify(ret_data)
    else:
        ret_data = {
            "code": 10003,
            "errors": {
                "body": [
                    "未登录"
                ]
            },
            "message": "fail"
        }
        return jsonify(ret_data)


# 更新用户
@users_bp.route('/api/user', methods=['PUT'])
@login_required
def user_update():
    email = request.args.get('email')
    new_bio = request.args.get('bio')
    new_image = request.args.get('image')
    if current_user.is_authenticated:
        current_user.bio = new_bio
        current_user.image = new_image
        current_user.email = email
        current_user.token = create_refresh_token(identity=current_user.username)
        db.session.add(current_user)
        db.session.commit()
        ret_data = {
            "code": 10000,
            "data": {"user": {
                "email": current_user.email,
                "token": current_user.token,
                "username": current_user.username,
                "bio": current_user.bio,
                "image": current_user.image,

            }
            },
            "message": "success",
            "body": "成功更新用户"
        }
        return jsonify(ret_data)
    else:
        ret_data = {
            "code": 10003,
            "errors": {
                "body": [
                    "未登录"
                ]
            },
            "message": "fail"
        }
        return jsonify(ret_data)


# 查询指定用户个人资料(当前用户需登录)
@users_bp.route('/api/profiles/<username>', methods=['GET'])
def user_profiles(username):
    # 这里查询的是目标用户，当前登陆的是exist_user
    target_user = User.query.filter(User.username == username).first()
    if current_user.is_authenticated:
        ret_data = {
            "code": 10000,
            "data": {"profile": {
                "username": target_user.username,
                "bio": target_user.bio,
                "image": target_user.bio,
                "following": current_user.is_following(target_user)}
            },
            "message": "null"}
        return jsonify(ret_data)
    else:
        ret_data = {
            "code": 10003,
            "errors": {
                "body": [
                    "未登录"
                ]
            },
            "message": "fail"
        }
        return jsonify(ret_data)


# 关注用户
@users_bp.route('/api/profiles/<username>/follow', methods=['POST'])
def user_follow(username):
    if current_user.is_authenticated:
        target_user = User.query.filter(User.username == username).first()
        current_user.follow(target_user)
        ret_data = {
            "code": 10000,
            "data": {"profile": {
                "username": target_user.username,
                "bio": target_user.bio,
                "image": target_user.bio,
                "following": current_user.is_following(target_user)}},
            "message": "null"}
        return jsonify(ret_data)
    else:
        ret_data = {
            "code": 10003,
            "errors": {
                "body": [
                    "can't be empty"
                ]
            },
            "message": "no auth"
        }
        return jsonify(ret_data)


# 取消关注用户
@users_bp.route('/api/profiles/<username>/follow', methods=['DELETE'])
def user_unfollow(username):
    if current_user.is_authenticated:
        target_user = User.query.filter(User.username == username).first()
        current_user.unfollow(target_user)
        ret_data = {
            "code": 10000,
            "data":{"profile": {
                "username": target_user.username,
                "bio": target_user.bio,
                "image": target_user.bio,
                "following": current_user.is_following(target_user)}},
            "message": "null"}
        return jsonify(ret_data)
    else:
        ret_data = {
            "code": 10003,
            "errors": {
                "body": [
                    "can't be empty"
                ]
            },
            "message": "no auth"
        }
        return jsonify(ret_data)

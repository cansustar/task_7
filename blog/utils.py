from flask import current_app
from itsdangerous import TimedSerializer as Serializer
from flask_mail import Message
from blog.estensions import mail
from itsdangerous import BadSignature, SignatureExpired
from blog.estensions import db
from blog.settings import Operations


# TimedSER..模块可以获得一个序列化对象，这个类的构造方法接收一个密钥作为参数，用来生成签名，密钥使用了配置变量的值
# 可选的expire_in参数用来设置密钥的过期时间，默认为3600秒
def generate_token(user, operation, expire_in=None, **kwargs):
    s = Serializer(current_app.config['SECRET_KEY', expire_in])
    # 接着创建了一个字典，该字典存储的值将被写入令牌的负载中，
    # id值通过传入的user对象获取，
    # operation变量为创建令牌需要进行确认的操作，以类的形式存储在了settings模块中
    data = {'id': user.id, 'operation': operation}
    # 也可以传入关键字参数，用update（）方法更新到字典中
    data.update(**kwargs)
    # dumps（）接收包含数据的字典作为参数。
    # 它会根据过期时间创建头部（Header），然后将数据编码到JWS的负载(payload)中，再使用密钥对令牌进行签名，最后将签名序列化后生成令牌值
    # data字典写入序列化对象，它会返回生成的令牌值。
    return s.dumps(data)


# 验证并解析确认令牌
def validate_token(user, token, operation):
    # 首先使用和创建令牌时相同的密钥创建一个序列化对象，
    # 该对象提供一个loads()方法，接收令牌值token作为参数，返回从负载中提取出的数据
    # 如果提取失败，通常会抛出SignatureExpired(签名过期)或者BadSignature(签名不匹配),在这种情况下返回false
    s = Serializer(current_app.config['SECRET_KEY'])
    try:
        data = s.loads(token)
    except (SignatureExpired, BadSignature):
        return False
    # 如果数据提取成功，会验证提取出的operation值是否与传入的operation参数匹配，即要确保执行正确的操作
    # 另外还会验证数据中的用户id值与当前用户的id值是否相同，避免恶意用户获取令牌值的情况
    if operation != data.get('operation') or user.id != data.get('id'):
        return False

    if operation == Operations.CONFIRM:
        user.confirmed = True
    else:
        return False
    db.session.commit()


# 发送确认邮件

# 发送邮件的通用发信函数

def send_mail(subject, to, body, template, **kwargs):
    message = Message(subject, recipients=[to], body=body)
    mail.send(message)


# 发送确认邮件
def send_confirm_email(user, token, to=None):
    send_mail(subject='注册', to=to or user.email, template='confirm', user=user, token=token)

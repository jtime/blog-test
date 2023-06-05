import os
#from dotenv import load_dotenv
from flask import Flask, render_template, redirect, url_for, flash, request, abort
from flask_bootstrap import Bootstrap
from flask_ckeditor import CKEditor
from datetime import date
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from forms import CreatePostForm, RegisterForm, LoginForm, CommentForm
from flask_gravatar import Gravatar
from functools import wraps


app = Flask(__name__)
app.config['SECRET_KEY'] = '8BYkEfBA6O6donzWlSihBXox7C0sKR6b'
ckeditor = CKEditor(app)
Bootstrap(app)
gravatar = Gravatar(app,
                    size=100,
                    rating='g',
                    default='retro',
                    force_default=False,
                    force_lower=False,
                    use_ssl=False,
                    base_url=None)


##CONNECT TO DB
#app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blog.db'
#遠端
# load_dotenv()
# xx = os.getenv("DATABASE_URL")
# print(xx)
# app.config['SQLALCHEMY_DATABASE_URI'] =xx
#近端
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')

#postgres://blog_test_user:yApCNL9nKDYXEBB7KAyFpEkck1QMyiXu@dpg-cht1933hp8u4v7rusr2g-a.oregon-postgres.render.com/blog_test
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.app_context().push()
db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)
#login_manager.login_view='login'


##CONFIGURE TABLES

class BlogPost(db.Model):
    __tablename__ = "blog_posts"
    #一對多的多
    #多要設一個外鍵
    author_id = db.Column(db.Integer, db.ForeignKey("blog_users.id"))  
    
    id = db.Column(db.Integer, primary_key=True)
    author = db.Column(db.String(250), nullable=False)
    title = db.Column(db.String(250), unique=True, nullable=False)
    subtitle = db.Column(db.String(250), nullable=False)
    date = db.Column(db.String(250), nullable=False)
    body = db.Column(db.Text, nullable=False)
    img_url = db.Column(db.String(250), nullable=False)
    #一對多的多
    #設定雙向關係
    author = relationship("Users", back_populates="posts")
    comments = relationship("Comment", back_populates="parent_post")

class Users(UserMixin, db.Model):
    __tablename__ = "blog_users"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(1000))
    email = db.Column(db.String(300), unique=True)
    password = db.Column(db.String(300))
    # 一對多的一
    # 設定雙向關係
    posts = relationship("BlogPost", back_populates="author")
    comments = relationship("Comment", back_populates="comment_author")

    def __init__(self, email, name, password):
        """初始化"""
        self.email = email
        self.name = name
        self.password = generate_password_hash(password)
        print(self.password)
    
    def check_password(self, password):
        """檢查使用者密碼"""
        print(check_password_hash(self.password, password))
        return check_password_hash(self.password, password)
    
class Comment(db.Model):
    __tablename__ = "comments"
    id = db.Column(db.Integer, primary_key=True)
    #一對多的多
    #多要設一個外鍵
    author_id = db.Column(db.Integer, db.ForeignKey("blog_users.id"))
    #一對多的多
    #多要設一個外鍵
    post_id = db.Column(db.Integer, db.ForeignKey("blog_posts.id"))
    #設定雙向關係
    comment_author = relationship("Users", back_populates="comments")
    parent_post = relationship("BlogPost", back_populates="comments")
    #***************Child Relationship*************#
    text = db.Column(db.Text, nullable=False)
    
db.create_all()

def admin_only(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if current_user.id != 1:
            return abort(403)
        return f(*args, **kwargs)
    return decorated_function

@app.errorhandler(403)
def forbidden(error):
    return render_template('403.html'), 403

@login_manager.user_loader
def load_user(id):
    return Users.query.get(int(id))


@app.route('/')
def get_all_posts():
    posts = BlogPost.query.all()
    return render_template("index.html", all_posts=posts)


@app.route('/register', methods=["GET", "POST"])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        if Users.query.filter_by(email=form.email.data).first():
            #User already exists
            flash("You've already signed up with that email, log in instead!")
            return redirect(url_for('login'))
        new_user = Users(
            name = form.name.data,
            email =  form.email.data,
            password = form.password.data,
        )
        db.session.add(new_user)
        db.session.commit()
        login_user(new_user)
        return redirect(url_for('get_all_posts'))
    return render_template("register.html", form=form)


@app.route('/login', methods=["GET", "POST"])
def login():
    #20230528測試flash問題
    # if current_user.is_authenticated:
    #     return redirect(url_for('get_all_posts'))
    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data
        user = Users.query.filter_by(email=email).first()
        if user is not None:
            if user.check_password(password):
                login_user(user)
                flash("您已经成功登入系统")
                # next = request.args.get('next')
                # if next is None or not next.startswith('/'):
                #     next = url_for('get_all_posts')
                # return redirect(next)
                return redirect(url_for('get_all_posts'))
            else:
                flash("密码错误，请重试")
        else:
            flash("找不到匹配的用户，请检查邮箱或进行注册")
        
    return render_template("login.html", form=form)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('get_all_posts'))


@app.route("/post/<int:post_id>", methods=["GET", "POST"])
def show_post(post_id):
    #comment_form = CommentForm()
    # requested_post = BlogPost.query.get(post_id)
    # return render_template("post.html", post=requested_post, current_user=current_user, form=comment_form)
    #20230528
    form = CommentForm()
    requested_post = BlogPost.query.get(post_id)

    if form.validate_on_submit():
        if not current_user.is_authenticated:
            flash("You need to login or register to comment.")
            return redirect(url_for("login"))

        new_comment = Comment(
            text=form.comment_text.data,
            comment_author=current_user,
            parent_post=requested_post
        )
        db.session.add(new_comment)
        db.session.commit()

    return render_template("post.html", post=requested_post, form=form, current_user=current_user)



@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/contact")
def contact():
    return render_template("contact.html")


@app.route("/new-post", methods=["GET", "POST"])
@admin_only
def add_new_post():
    form = CreatePostForm()
    if form.validate_on_submit():
        new_post = BlogPost(
            title=form.title.data,
            subtitle=form.subtitle.data,
            body=form.body.data,
            img_url=form.img_url.data,
            author=current_user,
            date=date.today().strftime("%B %d, %Y")
        )
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for("get_all_posts"))
    return render_template("make-post.html", form=form)


@app.route("/edit-post/<int:post_id>", methods=["GET", "POST"])
@admin_only
def edit_post(post_id):
    post = BlogPost.query.get(post_id)
    edit_form = CreatePostForm(
        title=post.title,
        subtitle=post.subtitle,
        img_url=post.img_url,
        author=post.author,
        body=post.body
    )
    if edit_form.validate_on_submit():
        post.title = edit_form.title.data
        post.subtitle = edit_form.subtitle.data
        post.img_url = edit_form.img_url.data
        post.author = edit_form.author.data
        post.body = edit_form.body.data
        db.session.commit()
        return redirect(url_for("show_post", post_id=post.id))

    return render_template("make-post.html", form=edit_form)


@app.route("/delete/<int:post_id>")
@admin_only
def delete_post(post_id):
    post_to_delete = BlogPost.query.get(post_id)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for('get_all_posts'))


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)

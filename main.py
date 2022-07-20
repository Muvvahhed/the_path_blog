from dotenv import load_dotenv
import os
from flask import Flask, render_template, redirect, url_for, flash, request, abort
from flask_bootstrap import Bootstrap
from flask_ckeditor import CKEditor
from datetime import date
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from flask_login import UserMixin, login_user, LoginManager, current_user, logout_user
from forms import CreatePostForm, RegisterForm, LoginForm, CommentForm
from flask_gravatar import Gravatar
from functools import wraps
import smtplib
import socket


socket.getaddrinfo('localhost', 8080)

app = Flask(__name__)
app.config['SECRET_KEY'] = '8BYkEfA6O6donzWlSihBXox7C0sKR6b'

load_dotenv("environment.env")

ckeditor = CKEditor(app)
Bootstrap(app)

# CONNECT TO DB
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blog.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# CREATING FLASK LOGIN MANAGER
login_manager = LoginManager()
login_manager.init_app(app)

# CREATING Gravatar
gravatar = Gravatar(
    app=app,
    size=100,
    rating='g',
    default='mp',
    force_default=False,
    force_lower=False,
    use_ssl=False,
    base_url=None
)


# CREATING USER LOADER
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# CREATING ADMIN ACCESS
def admin_only(function):
    @wraps(function)
    def decorated_function(*args, **kwargs):
        if current_user.is_authenticated:
            if current_user.id in (1, 2):
                return function(*args, **kwargs)

        return abort(403)

    return decorated_function


# SENDS EMAIL
def send_message(data):
    with smtplib.SMTP("smtp.gmail.com") as connection:
        connection.starttls()
        connection.login(user="musaturquoise@gmail.com", password=os.getenv("EMAIL_PASSWORD"))
        connection.sendmail(from_addr=f"musaturquoise@gmail.com",
                            to_addrs=f"muwaheedmustapha@gmail.com",
                            msg=f"Subject: Message from blog\n\n"
                                f"Name : {data['name']}\n"
                                f"Email: {data['email']}\n"
                                f"Phone Number: {data['phone']}\n"
                                f"Message: {data['message']}"
                            )
        print("success")


# CONFIGURE TABLES
class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String, unique=True, nullable=False)
    name = db.Column(db.String, nullable=False)
    password = db.Column(db.String, nullable=False)

    # This will act like a List of BlogPost objects attached to each User.
    # The "author" refers to the author property in the BlogPost class.
    posts = relationship("BlogPost", back_populates="author")

    # This will act like a List of Comment objects attached to each User.
    # The "comment_author" refers to the author property in the Comment class.
    comments = relationship("Comment", back_populates="comment_author")


class BlogPost(db.Model):
    __tablename__ = "blog_posts"
    id = db.Column(db.Integer, primary_key=True)

    # Create Foreign Key, "users.id" the users refers to the tablename of User.
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    # Create reference to the User object, the "posts" refers to the posts property in the User class.
    author = relationship("User", back_populates="posts")

    title = db.Column(db.String(250), unique=True, nullable=False)
    subtitle = db.Column(db.String(250), nullable=False)
    date = db.Column(db.String(250), nullable=False)
    body = db.Column(db.Text, nullable=False)
    img_url = db.Column(db.String(250), nullable=False)

    # This will act like a List of Comment objects attached to each Post.
    # The "comment_author" refers to the parent_post property in the Comment class.
    comments = relationship("Comment", back_populates="parent_post")


class Comment(db.Model):
    __tablename__ = "comments"
    id = db.Column(db.Integer, primary_key=True)

    # Create Foreign Key, "users.id" the users refers to the tablename of User.
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    # Create reference to the User object, the "comments" refers to the comments property in the User class.
    comment_author = relationship("User", back_populates="comments")
    # Create Foreign Key, "blog_posts.id" the blog_posts refers the tablename of BlogPost
    post_id = db.Column(db.Integer, db.ForeignKey("blog_posts.id"))
    # Create reference to the User object, the "comments" refers to the comments property in the BlogPost class.
    parent_post = relationship("BlogPost", back_populates="comments")

    text = db.Column(db.Text, nullable=False)


db.create_all()


@app.route('/')
def get_all_posts():
    posts = BlogPost.query.all()
    return render_template("index.html", all_posts=posts)


@app.route('/register', methods=["POST", 'GET'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data

        if User.query.filter_by(email=email).first():
            flash("You've already signed up with this email, login instead")
            return redirect(url_for("login"))

        hashed_password = generate_password_hash(
            password=password,
            method="pbkdf2:sha256",
            salt_length=8
        )
        new_user = User(
            email=email,
            password=hashed_password,
            name=form.name.data
        )
        db.session.add(new_user)
        db.session.commit()
        login_user(new_user)
        return redirect(url_for('get_all_posts'))
    return render_template("register.html", form=form)


@app.route('/login', methods=["POST", "GET"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data
        user = User.query.filter_by(email=email).first()

        # checks if the user exists
        if user:
            if check_password_hash(user.password, password):
                login_user(user)
                return redirect(url_for("get_all_posts"))
            else:
                flash("Password Incorrect, please try again.")
        else:
            flash("This email does not exist, please try again")
    return render_template("login.html", form=form)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('get_all_posts'))


@app.route("/post/<int:post_id>", methods=["POST", "GET"])
def show_post(post_id):
    requested_post = BlogPost.query.get(post_id)
    comments = Comment.query.filter_by(post_id=post_id).all()
    comment_form = CommentForm()
    if comment_form.validate_on_submit():
        if current_user.is_authenticated:
            new_comment = Comment(
                text=comment_form.comment.data,
                comment_author=current_user,
                parent_post=requested_post,
            )
            db.session.add(new_comment)
            db.session.commit()
            comment_form.comment.data = ""
            return redirect(url_for("show_post", post_id=post_id))
        else:
            flash("You need to login or register to be able to comment")
            return redirect(url_for("login"))
    return render_template("post.html", post=requested_post, comment_form=comment_form, comments=comments)


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        form_data = request.form
        send_message(form_data)
        return render_template("contact.html", is_sent=True)
    return render_template("contact.html", is_sent=False)


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


@app.route("/edit-post/<int:post_id>", methods=["POST", "GET"])
@admin_only
def edit_post(post_id):
    post = BlogPost.query.get(post_id)
    edit_form = CreatePostForm(
        title=post.title,
        subtitle=post.subtitle,
        img_url=post.img_url,
        body=post.body
    )
    if edit_form.validate_on_submit():
        post.title = edit_form.title.data
        post.subtitle = edit_form.subtitle.data
        post.img_url = edit_form.img_url.data
        post.body = edit_form.body.data
        db.session.commit()
        return redirect(url_for("show_post", post_id=post.id))

    return render_template("make-post.html", form=edit_form)


@app.route("/delete/<int:post_id>")
@admin_only
def delete_post(post_id):
    post_to_delete = BlogPost.query.get(post_id)
    post_comments = post_to_delete.comments
    db.session.delete(post_to_delete)
    db.session.commit()
    for comment in post_comments:
        db.session.delete(comment)
        db.session.commit()
    return redirect(url_for('get_all_posts'))


@app.route("/delete_comment/<int:comment_id>")
@admin_only
def delete_comment(comment_id):
    comment_to_delete = Comment.query.get(comment_id)
    post = comment_to_delete.parent_post
    db.session.delete(comment_to_delete)
    db.session.commit()
    return redirect(url_for("show_post", post_id=post.id))


if __name__ == "__main__":
    app.run(debug=True)

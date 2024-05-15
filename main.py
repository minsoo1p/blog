from flask import Flask, render_template, redirect, url_for, request, flash
from flask_bootstrap import Bootstrap5
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Integer, String, Text, Column, ForeignKey
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired, URL
from flask_ckeditor import CKEditor, CKEditorField
from datetime import date, datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from sqlalchemy.orm import relationship
from forms import PostForm, MakeComments
import os
'''
Make sure the required packages are installed: 
Open the Terminal in PyCharm (bottom left). 

On Windows type:
python -m pip install -r requirements.txt

On MacOS type:
pip3 install -r requirements.txt

This will install the packages from the requirements.txt for this project.
'''

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get("FLASK_KEY")
Bootstrap5(app)
app.config['CKEDITOR_PKG_TYPE'] = 'basic'
ckeditor = CKEditor(app)

# CREATE DATABASE
class Base(DeclarativeBase):
    pass

app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DB_URI",'sqlite:///posts.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(model_class=Base)
db.init_app(app)


# CONFIGURE USER TABLE (parent)
class User(db.Model, UserMixin):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    name = db.Column(db.String(1000))

    posts = relationship("BlogPost", back_populates="author")
    comments = relationship("Comment", back_populates="user")

# CONFIGURE POSTS TABLE (child)
class BlogPost(db.Model):
    __tablename__ = 'post'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(250), unique=True, nullable=False)
    subtitle = db.Column(db.String(250), nullable=False)
    date = db.Column(db.String(250), nullable=False)
    body = db.Column(db.Text, nullable=False)
    img_url = db.Column(db.String(250), nullable=False)

    author_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    author = relationship("User", back_populates="posts")
    
class Comment(db.Model) :
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(250), nullable=False)
    post_id = db.Column(db.Integer, nullable=False)

    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    user = relationship("User", back_populates="comments")

with app.app_context():
    db.create_all()  

#gravatar


# for Login
login_manager = LoginManager()
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)


# for ERROR
@app.errorhandler(401)
def unauthorized(e):
    return render_template('401.html'), 401



# working area 
@app.route('/')
def get_all_posts():
    contents = db.session.query(BlogPost).all()
    return render_template("index.html", all_posts=contents, logged_in = current_user.is_authenticated, user=current_user)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == "POST" :
        Email = request.form['email']
        Password = request.form['password']
        user = User.query.filter_by(email=Email).first()
        if user and check_password_hash(user.password, Password) :
            login_user(user)
            contents = db.session.query(BlogPost).all()
            return render_template("index.html", all_posts=contents, logged_in = current_user.is_authenticated, user=user)
        else : 
            if user : 
                flash('recheck your password')
                return redirect(url_for('login'))
            else : 
                flash('recheck your email')
                return redirect(url_for('login'))
    return render_template("login.html")

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST' :
        Name = request.form['name']
        Email = request.form['email']
        Password = request.form['password']
        hashed_password = generate_password_hash(Password, method='pbkdf2:sha256', salt_length=8)
        user = User.query.filter_by(email=Email).first() 
        if user :
            flash('You already have ID. Go to Login.')
            return redirect(url_for('register'))
        else :
            new_user = User ( name= Name, email=Email, password=hashed_password)
            db.session.add(new_user)
            db.session.commit()
            flash('log in with registered email')
            return redirect(url_for("login"))
    return render_template("register.html")

@app.route('/logout')
def logout():
    logout_user()
    contents = db.session.query(BlogPost).all()
    return render_template("index.html", all_posts=contents, logged_in = current_user.is_authenticated) 

## user 영역
@app.route('/post/<int:post_id>', methods=['GET', 'POST'])
@login_required
def show_post(post_id):
    contents = db.session.query(BlogPost).all()
    for content in contents : 
        if content.id == post_id :
            requested_post = content
        else : 
            pass
    form = MakeComments()
    comments = db.session.query(Comment).all()
    if form.validate_on_submit():
        new_comment = Comment ( text=form.text.data[3:-6], post_id=post_id, user_id=current_user.id)
        db.session.add(new_comment)
        db.session.commit()
        return redirect(url_for('show_post', post_id=post_id))
    return render_template("post.html", post=requested_post, comments=comments, form=form, id=current_user.id, logged_in = current_user.is_authenticated)

@app.route('/del_comment/<int:post_number>/<int:comment_number>')
@login_required
def del_comment(post_number, comment_number):
    comment_to_delete = Comment.query.get(comment_number)
    delete_user_id = comment_to_delete.user_id
    if delete_user_id == current_user.id : 
        comment_id = comment_number
        comment_to_delete = Comment.query.get(comment_id)
        db.session.delete(comment_to_delete)
        db.session.commit()
    else : 
        pass
    return redirect(url_for('show_post', post_id=post_number))

## 관리자 영역

@app.route('/add/<int:id>', methods=['GET', 'POST'])
@login_required
def add_new_post(id):
    add_or_edit = True
    form = PostForm()
    current_time = datetime.now()
    formatted_time = current_time.strftime("%B %d, %Y")
    
    if form.validate_on_submit():
        Title = form.title.data
        Subtitle = form.subtitle.data
        Date = formatted_time
        Body = form.body.data
        Author = current_user
        Img_url = form.img_url.data
        new_post = BlogPost (title=Title, subtitle=Subtitle, date=Date, body=Body, author=Author, img_url=Img_url)
        db.session.add(new_post)
        db.session.commit()
        contents = db.session.query(BlogPost).all()
        user = User.query.filter_by(id=id).first()    
        return render_template('index.html', all_posts=contents, user=user)
    return render_template('make-post.html', form=form, add_or_edit=add_or_edit, id=id, logged_in=current_user.is_authenticated)

@app.route('/edit/<int:number>/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_post(number, id):
    content = BlogPost.query.filter_by(id=number).first()

    class EditForm(FlaskForm):
        title = StringField('Title', default=content.title)
        subtitle = StringField('Subtitle', default=content.subtitle)
        body = CKEditorField('Body', default=content.body)  
        img_url = StringField('Img_URL', default=content.img_url)
        submit = SubmitField('Submit')
        
    form = EditForm()
    add_or_edit = False
    if form.validate_on_submit():
        Title = form.title.data
        Subtitle = form.subtitle.data
        Body = form.body.data
        Img_url = form.img_url.data
        blog = BlogPost.query.filter_by(id=number).first()
        blog.title = Title
        blog.subtitle = Subtitle
        blog.body = Body
        blog.img_url = Img_url
        db.session.commit()
        return redirect(url_for('show_post', post_id=number))
    return render_template('make-post.html', form=form, add_or_edit=add_or_edit,id = id, logged_in=current_user.is_authenticated)



# TODO: delete_post() to remove a blog post from the database
@app.route('/delete/<int:number>')
@login_required
def delete(number):
    post_id = number
    post_to_delete = BlogPost.query.get(post_id)
    if current_user.id == 1 :
        db.session.delete(post_to_delete)
        db.session.commit()
    else : 
        pass
    return redirect(url_for('get_all_posts'))

# Below is the code from previous lessons. No changes needed.
@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/contact")
def contact():
    return render_template("contact.html")


if __name__ == "__main__":
    app.run(debug=True, port=5003)

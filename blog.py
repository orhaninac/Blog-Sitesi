from flask import Flask,render_template,flash,redirect,url_for,session,logging,request
from flask_mysqldb import MySQL
from wtforms import Form,StringField,TextAreaField,PasswordField,validators
from passlib.handlers.sha2_crypt import sha256_crypt
import email_validator
from functools import wraps

app = Flask(__name__)
#MYSQL DataBase'ine bağlanıyor
app.secret_key="blog" # kayıttan sonra mesaj döndürmek için "RUNTIME" hatasını engeller
app.config["MYSQL_HOST"]="localhost" # Eğer uzak sunucu olursa adresini yaz
app.config["MYSQL_USER"]="root"
app.config["MYSQL_PASSWORD"]=""
app.config["MYSQL_DB"]="blog"
app.config["MYSQL_CURSORCLASS"]="DictCursor"

mysql=MySQL(app) #MYSQL'den bir nesne üretiyor

#kullanıcı giriş decorater
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "logged_in" in session:
            return f(*args, **kwargs)
        else:
            flash("Lütfen giriş yapın...","danger")
            return redirect(url_for("login"))

    return decorated_function

# Kullanıcı Kayıt Formu
class RegisterForm(Form):
    name=StringField("İsim Soyisim",validators=[validators.length(min=4,max=25)])
    username=StringField("Kullanıcı Adı",validators=[validators.length(min=5,max=(25))])
    email=StringField("Email Adresi",validators=[validators.Email(message="Lütfen Geçerli Bir Email Adresi Girin")])
    password=PasswordField("Parola",validators=[
        validators.DataRequired(message="Lütfen Bir Parola Belirleyin"),
        validators.EqualTo(fieldname="confirm",message="Parolanız Uyuşmuyor")
    ])
    confirm=PasswordField("Parola Doğrula")

# Kayıt olma sayfası
@app.route("/register",methods=["GET","POST"])
def register():
    form=RegisterForm(request.form)

    if request.method=="POST" and form.validate():
        name=form.name.data
        username=form.username.data
        email=form.email.data
        password=sha256_crypt.encrypt(form.password.data)

        cursor=mysql.connection.cursor()
        sorgu="insert into users (name,email,username,password) values(%s,%s,%s,%s)"

        cursor.execute(sorgu,(name,email,username,password))
        mysql.connection.commit()
        cursor.close()
        flash("Başarıyla Kayıt Oldunuz","success")
        return redirect(url_for("login"))
    else :        
        return render_template("register.html",form=form)

#Kullanıcı Giriş Formu
class LoginForm(Form):
    username=StringField("Kullanıcı Adı")
    password=PasswordField("Parola")

#Login işlemi
@app.route("/login",methods=["GET","POST"])
def login():
    form=LoginForm(request.form)
    if request.method=="POST":
        username=form.username.data
        password_entered=form.password.data

        cursor=mysql.connection.cursor()

        sorgu="select * from users where username=%s"
        result=cursor.execute(sorgu,(username,))
        
        if result>0 :
            data=cursor.fetchone()
            real_password=data["password"]
            if sha256_crypt.verify(password_entered,real_password):
                flash("Başarıyla Girş Yaptınız","success")
                session["logged_in"]=True
                session["username"]=username
                return redirect(url_for("index"))
            else:
                flash("Parola uyuşmuyor","danger")
                return redirect(url_for("login"))    
        else:
            flash("Böyle bir kullanıcı bulunmuyor","danger")
            return redirect(url_for("login"))
    return render_template("login.html",form=form)

#Ana Sayfa
@app.route("/")
def index():
    return render_template("index.html")

#Hakkımda Sayfası
@app.route("/about")
def about():
    return render_template("about.html")

#Kontrol Paneli
@app.route("/dashboard")
@login_required
def dashboard():
    cursor=mysql.connection.cursor()
    sorgu=("select * from articles where author=%s")

    result=cursor.execute(sorgu,(session["username"],))
    if result>0:
        articles=cursor.fetchall()
        return render_template("dashboard.html",articles=articles)
    else:
        return render_template("dashboard.html")

#Logout işlemi
@app.route("/logout")
def logout():
    session.clear()
    flash("Çıkış yapıldi","info")
    return redirect(url_for("index"))

#makale ekleme 
@app.route("/addarticle",methods=["GET","POST"])
def addarticles():
    form=articlesForm(request.form)
    if request.method == "POST" and form.validate():
        title=form.title.data
        content=form.content.data
        cursor=mysql.connection.cursor()
        sorgu="insert into articles(title,author,content) values(%s,%s,%s)"

        cursor.execute(sorgu,(title,session["username"],content))
        mysql.connection.commit()
        cursor.close()
        flash("Makale başarıyla eklendi","success")
        return redirect(url_for("dashboard"))
    return render_template("addarticles.html",form=form)

#Makale Sayfası
@app.route("/articles")
def articles():
    cursor=mysql.connection.cursor()
    sorgu=("select * from articles")
    
    result =cursor.execute(sorgu)
    if result>0:
        articles=cursor.fetchall()
        return render_template("articles.html",articles=articles)
    else:
        return render_template("articles.html")

#makale silme
@login_required
@app.route("/delete/<string:id>")
def delete(id):
    cursor=mysql.connection.cursor()
    sorgu="select * from articles where author=%s and id=%s"
    result=cursor.execute(sorgu,(session["username"],id))
    if result>0:
        sorgu2="delete from articles where id=%s"
        cursor.execute(sorgu2,(id,)) 
        mysql.connection.commit()
        flash("makale silindi","success")
        return redirect(url_for("dashboard"))
    else:
        flash("Böyle bir makale yok veya silmeye yetkiniz yok..")
        return redirect(url_for("index"))

#makale güncelleme
@login_required
@app.route("/edit/<string:id>",methods=["GET","POST"])
def update(id):
    
    if request.method=="GET":
        cursor=mysql.connection.cursor()
        sorgu="select * from articles where id=%s and author=%s"

        result=cursor.execute(sorgu,(id,session["username"]))
        if result == 0:
            flash("böyle bir makale yok veya bu işlem için yetkiniz yok")
            return redirect(url_for("index"))
        else:
            article=cursor.fetchone()
            form=articlesForm()

            form.title.data=article["title"]
            form.content.data=article["content"]
            return render_template("update.html",form=form)
       
    else:
        form=articlesForm(request.form)

        newItem=form.title.data
        newContent=form.content.data

        sorgu2="update articles set title=%s, content=%s where id=%s"

        cursor=mysql.connection.cursor()
        cursor.execute(sorgu2,(newItem,newContent,id))
        mysql.connection.commit()

        flash("Makale başarıyla güncellendi","success")
        return redirect(url_for("dashboard"))

#makale detay
@app.route("/article/<string:id>")
def article(id):
    cursor=mysql.connection.cursor()
    sorgu="select * from articles where id=%s"
    result=cursor.execute(sorgu,(id,))
    if result>0:
        article=cursor.fetchone()
        return render_template("article.html",article=article)
    else:
        return render_template("article.html")
#makale ekleme formu
class articlesForm(Form):
    title=StringField("Makale Başlığı",validators=[validators.Length(min=5,max=100)])
    content=TextAreaField("Makale İçeriği",validators=[validators.Length(min=10)])
@app.route("/search",methods=["GET","POST"])
def search():
    if request.method=="GET":
        return redirect(url_for("index"))
    else:
        keyword=request.form.get("keyword")

    cursor=mysql.connection.cursor()

    sorgu=("select * from articles where title like '%"+keyword+"%'")
    result=cursor.execute(sorgu)
    if result==0:
        flash("Aradığınız kelimeyle ilgili makale bulunamadı...","danger")
        return redirect(url_for("articles"))
    else:
        articles=cursor.fetchall()
        return render_template("articles.html",articles=articles)
if __name__=="__main__":
    app.run(debug=True)

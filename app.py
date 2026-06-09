import os   
from datetime import datetime                        
from flask import Flask,render_template,request,redirect,url_for,flash,session,abort
from werkzeug.security import generate_password_hash,check_password_hash
from werkzeug.utils import secure_filename
from flask_sqlalchemy import SQLAlchemy
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns

#************************************************************************************************************************

curr_dir=os.path.dirname(os.path.abspath(__file__))
app=Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI']='sqlite:///HouseholdServices.sqlite3'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS']=False
app.config['SECRET_KEY']='secretkey'
app.config['PASSWORD_HASH']='passwordhash'
app.config['UPLOAD_EXTENSION']=['.pdf']
app.config['UPLOAD_PATH']=os.path.join(curr_dir,'static','pdfs')

db=SQLAlchemy()
db.init_app(app)
app.app_context().push()

#************************************************************************************************************************
class Alluser(db.Model):
    __tablename__='alluser'
    id=db.Column(db.Integer,primary_key=True)
    username=db.Column(db.String(80),unique=True,nullable=False)
    email=db.Column(db.String(80),nullable=True)
    password=db.Column(db.String(80),nullable=False)
    address=db.Column(db.String(80),nullable=True)
    pincode=db.Column(db.Integer,nullable=True)
    isAdmin=db.Column(db.Boolean,default=False)
    isProfessional=db.Column(db.Boolean,default=False)
    isCustomer=db.Column(db.Boolean,default=False)
    isApproved=db.Column(db.Boolean,default=False)
    isFlagged=db.Column(db.Boolean,default=False)
    averageRating=db.Column(db.Float,default=0.0)
    ratingCount=db.Column(db.Integer,default=0)
    professionalPdf=db.Column(db.String(80),nullable=True)
    professionalExperience=db.Column(db.String(80),nullable=True)

    serviceId = db.Column(db.Integer, db.ForeignKey('services.id', ondelete="SET NULL"), nullable=True)  
    service = db.relationship('Services', back_populates="professionals")
    customerRequests = db.relationship('ServiceRequest',back_populates='customer',foreign_keys="ServiceRequest.customerId")
    professionalRequests = db.relationship('ServiceRequest',back_populates='professional',foreign_keys="ServiceRequest.professionalId")

class Services(db.Model):
    __tablename__='services'
    id=db.Column(db.Integer,primary_key=True)
    serviceName=db.Column(db.String(80),unique=True,nullable=False)
    serviceDescription=db.Column(db.String(80),nullable=False)
    basePrice=db.Column(db.Integer,nullable=True)
    timeRequired=db.Column(db.String(80),nullable=True)
    
    professionals=db.relationship('Alluser',back_populates="service",cascade="all, delete")         
    request=db.relationship('ServiceRequest',back_populates="service",cascade="all, delete-orphan")      

class ServiceRequest(db.Model):
    __tablename__ = 'serviceRequest'
    id = db.Column(db.Integer, primary_key=True)
    serviceId = db.Column(db.Integer, db.ForeignKey('services.id'), nullable=True)
    customerId = db.Column(db.Integer, db.ForeignKey('alluser.id'), nullable=False)
    professionalId = db.Column(db.Integer, db.ForeignKey('alluser.id'), nullable=True)
    reqType = db.Column(db.String(10), nullable=False)                         
    description = db.Column(db.Text, nullable=True)                            
    status = db.Column(db.String(80), nullable=True)                          
    dateCreated = db.Column(db.Date, nullable=False, default=datetime.now().date())
    dateClosed = db.Column(db.Date, nullable=True)
    ratingByCustomer = db.Column(db.Float, default=0.0)
    reviewByCustomer = db.Column(db.String(80), nullable=True)

    service = db.relationship('Services', back_populates="request")
    customer = db.relationship('Alluser',back_populates="customerRequests", foreign_keys=[customerId])                                                                                                                                                    
    professional = db.relationship('Alluser',back_populates="professionalRequests", foreign_keys=[professionalId])

#************************************************************************************************************************
def createAdmin():
    with app.app_context():
        admin = Alluser.query.filter_by(isAdmin=True).first()
        if not admin:
            admin = Alluser(username="admin", password=generate_password_hash('789456123'), isAdmin=True, isApproved=True)
            db.session.add(admin)
            db.session.commit()
            print("Admin User Created Successfully")

#Initailizing the database
with app.app_context():
    db.create_all()
    createAdmin()
#************************************************************************************************************************
@app.route("/", methods=["GET","POST"])
def home():
    return render_template("home.html")

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        user=Alluser.query.filter_by(username=username).first()
        if user and check_password_hash(user.password,password):
            session['userId']=user.id
            session['isProfessional']=user.isProfessional
            session['isCustomer']=user.isCustomer
            session['username']=user.username


            if user.isFlagged:
                flash("Your account is Flagged. Please login with another account",'danger')
                return redirect("/login")
            if user.isProfessional:
                userType="professional"
                if user.isApproved==False:
                    flash("Your account is not Approved yet. Please wait for the Approval.",'danger')
                    return redirect("/login")
                if user.serviceId==None:
                    flash("Your service is not available yet. Please wait for approval.",'danger')
                    return redirect("/login")
                return redirect('/'+userType+'Dashboard')
            if user.isCustomer:
                userType="customer"
                flash("Login Successful !",'success')
                return redirect('/'+userType+'Dashboard')

        flash("Login Unsuccessful !. Please check your username and password",'danger')
    return render_template("login.html")
#************************************************************************************************************************
@app.route("/adminLogin", methods=["GET","POST"])
def adminLogin():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        admin=Alluser.query.filter_by(isAdmin=True).first()   # admin is sqlalchemy object
        if admin and check_password_hash(admin.password,password) :
            session['username']=username
            session['isAdmin']=True
            flash("Admin Login Successful !",'success')
            return redirect("/adminDashboard") 
    return render_template("adminLogin.html")

@app.route("/adminDashboard", methods=["GET","POST"])
def adminDashboard():
    if not session.get('isAdmin'):
        flash("Please login first !",'danger')
        return redirect("/login")
    services=Services.query.all()
    requests=ServiceRequest.query.all()
    unapprovedProfessionals=Alluser.query.filter_by(isProfessional=True,isApproved=False).all()
    
    if not unapprovedProfessionals:
        flash("No unapproved professionals available",'info')
    
    return render_template("adminDashboard.html", unapprovedProfessionals=unapprovedProfessionals, services=services, requests=requests,admin_name=session['username'])

@app.route("/adminDashboard/createService", methods=["GET", "POST"])
def createService():
    if not session.get('isAdmin'):
        flash("Please login first !",'danger')
        return redirect("/adminLogin")
    if request.method == "POST":
        serviceName = request.form.get("serviceName")
        serviceDescription = request.form.get("serviceDescription")
        basePrice = request.form.get("basePrice")
        timeRequired = request.form.get("timeRequired")
        
        service = Services(serviceName=serviceName, serviceDescription=serviceDescription, basePrice=basePrice, timeRequired=timeRequired)
        db.session.add(service)
        db.session.commit()
        flash("Service created successfully !",'success')
        return redirect("/adminDashboard")
    return render_template("createService.html")

@app.route("/adminDashboard/editService/<int:serviceId>", methods=["GET", "POST"])
def editService(serviceId):
    if not session.get('isAdmin'):
        flash("Please login first !",'danger')
        return redirect("/adminLogin")
    service = Services.query.get(serviceId)
    if service is None:
        flash("Service not found !",'danger')
        return redirect("/adminDashboard")
    if request.method == "POST":
        serviceName = request.form.get("serviceName")
        serviceDescription = request.form.get("serviceDescription")
        basePrice = request.form.get("basePrice")
        timeRequired = request.form.get("timeRequired")
        
        service.serviceName = serviceName
        service.serviceDescription = serviceDescription
        service.basePrice = basePrice
        service.timeRequired = timeRequired
        db.session.commit()
        flash("Service updated successfully !",'success')
        return redirect("/adminDashboard")
    return render_template("editService.html", service=service)

@app.route("/adminDashboard/deleteService/<int:serviceId>", methods=["GET", "POST"])
def deleteService(serviceId):
    if not session.get('isAdmin'):
        flash("Please login first !",'danger')
        return redirect("/adminLogin")
    service = Services.query.get(serviceId)
    approvedProfessionals=Alluser.query.filter_by(isProfessional=True,isApproved=True,serviceId=serviceId).all()
    for professional in approvedProfessionals:
        professional.isApproved=False
    db.session.delete(service)
    db.session.commit()
    flash("Service deleted successfully !",'success')
    return redirect("/adminDashboard")

@app.route("/adminDashboard/viewProfessional/<int:professionalId>", methods=["GET", "POST"])
def viewProfessional(professionalId):
    if not session.get('isAdmin'):
        flash("Please login first !",'danger')
        return redirect("/adminLogin")
    professional = Alluser.query.get(professionalId)
    return render_template("viewProfessional.html", professional=professional)

@app.route("/adminDashboard/approveProfessional/<int:professionalId>", methods=["GET", "POST"])
def approveProfessional(professionalId):
    if not session.get('isAdmin'):
        flash("Please login first !",'danger')
        return redirect("/AdminLogin")
    professional = Alluser.query.get(professionalId)
  
    professional.isApproved=True
    db.session.commit()
    flash("Professional approved successfully !",'success')
    return redirect("/adminDashboard")

@app.route("/adminDashboard/rejectProfessional/<int:professionalId>", methods=["GET", "POST"])
def rejectProfessional(professionalId):   
    if not session.get('isAdmin'):
        flash("Please login first !",'danger')
        return redirect("/adminLogin")
    professional = Alluser.query.get(professionalId)
    pdfFile=professional.professionalPdf
    if pdfFile:
        pathFile=os.path.join(app.config['UPLOAD_PATH'],pdfFile)
        if os.path.exists(pathFile):
            try:
                os.remove(pathFile)
                print("File deleted successfully")
            except Exception as e:
                print("Error deleting file:", str(e))
        else:
            print("File not found")
    db.session.delete(professional)
    db.session.commit()
    flash("Professional rejected successfully !",'success')
    return redirect("/adminDashboard")

@app.route("/adminDashboard/search", methods=["GET","POST"])
def adminSearch():
    if not session.get('isAdmin'):
        flash("Please login first !",'danger')
        return redirect("/adminLogin")
    searchType=request.args.get('searchType')
    searchQuery=request.args.get('searchQuery')
    if searchQuery:
        if searchType=='user':
            users=Alluser.query.filter(Alluser.username.like("%"+searchQuery+"%")).all()
            return render_template("adminSearch.html",users=users, adminName=session['username'])
        if searchType=='service':
            services=Services.query.filter(Services.serviceName.like("%"+searchQuery+"%")).all()
            return render_template("adminSearch.html",services=services, adminName=session['username'])
    else:
        users=Alluser.query.filter(Alluser.isApproved==True).all()
        services=Services.query.all()
        return render_template("adminSearch.html",users=users, adminName=session['username'],services=services)
    
@app.route("/adminDashboard/blockProfessional/<int:userId>", methods=["GET", "POST"])
def blockProfessional(userId):   
    if not session.get('isAdmin'):
        flash("Please login first !",'danger')
        return redirect("/adminLogin")
    professional = Alluser.query.get(userId)
    professional.isFlagged = True
    db.session.commit()
    flash("Professional blocked successfully !",'success')
    return redirect("/adminDashboard")

@app.route("/adminDashboard/unblockProfessional/<int:userId>", methods=["GET", "POST"])
def unblockProfessional(userId):   
    if not session.get('isAdmin'):
        flash("Please login first !",'danger')
        return redirect("/adminLogin")
    professional = Alluser.query.get(userId)
    professional.isFlagged = False
    db.session.commit()
    flash("Professional Unblocked successfully !",'success')
    return redirect("/adminDashboard")

@app.route("/adminDashboard/summary")
def adminSummary():
    if not session.get('isAdmin'):
        flash("Please login first !",'danger')
        return redirect("/adminLogin")
    customerCount=Alluser.query.filter_by(isCustomer=True).count()
    professionalCount=Alluser.query.filter_by(isProfessional=True).count()

    acceptedCount=ServiceRequest.query.filter_by(status="accepted").count()
    pendingCount=ServiceRequest.query.filter_by(status="pending").count()
    closedCount=ServiceRequest.query.filter_by(status="closed").count()
    rejectedCount=ServiceRequest.query.filter_by(status="rejected").count()

    img1=os.path.join(curr_dir,"static","images","img1.png")
    img2=os.path.join(curr_dir,"static","images","img2.png")

    status=["Accepted","Pending","Closed","Rejected"]
    counts=[acceptedCount,pendingCount,closedCount,rejectedCount] 
    plt.clf()
    plt.figure(figsize=(8, 6))
    plt.pie(counts,labels=status,colors=["green","yellow","orange","red"],autopct='%1.1f%%')
    plt.savefig(img2,format="png")

    roles=["Customer","Professional"]
    counts=[customerCount,professionalCount]

    plt.clf()
    plt.figure(figsize=(8, 6))
    sns.barplot(x=roles,y=counts)
   
    plt.xlabel("User Role")  
    plt.ylabel("No. of Count")
    plt.savefig(img1,format="png")

    

    return render_template("adminSummary.html",adminName=session['username'],customerCount=customerCount,professionalCount=professionalCount,
                           acceptedCount=acceptedCount,pendingCount=pendingCount,closedCount=closedCount,rejectedCount=rejectedCount)






#************************************************************************************************************************
@app.route("/professionalRegister", methods=["GET","POST"])
def professionalRegister():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        email = request.form.get("email")
        address = request.form.get("address")
        pincode = request.form.get("pincode")
        professionalPdf=request.files.get("professionalPdf")                    
        professionalExperience=request.form.get("professionalExperience")
        service=request.form.get("service")
        serviceId=Services.query.filter_by(serviceName=service).first().id
        user=Alluser.query.filter_by(username=username).first()
        if user:
            flash("Username already exists. Please choose a different username.",'danger')
            return redirect("/professionalRegister")
        fileName = secure_filename(professionalPdf.filename)
        if fileName!="":
            file_ext=os.path.splitext(fileName)[1]
            renamedFileName=username+file_ext
            if file_ext not in app.config['UPLOAD_EXTENSION']:
                abort(400)
            professionalPdf.save(os.path.join(app.config['UPLOAD_PATH'],renamedFileName))
        user=Alluser(username=username,password=generate_password_hash(password),email=email,address=address,pincode=pincode,serviceId=serviceId,isProfessional=True,isApproved=False,professionalPdf=renamedFileName,professionalExperience=professionalExperience)
        db.session.add(user)
        db.session.commit()
        flash("Professional Registration Successful !",'success')
        return redirect("/login")
    services=Services.query.all()
    return render_template("professionalRegister.html",services=services)


@app.route("/professionalDashboard", methods=["GET","POST"])
def professionalDashboard():
    if not session.get('isProfessional'):
        flash("Please login first !",'danger')
        return redirect("/login")
    pid=Alluser.query.filter_by(username=session['username']).first().id
    professional=Alluser.query.filter_by(id=pid).first()
    if professional.isApproved==False:
        flash("Your account is not approved yet. Please wait for approval.",'danger')
        return redirect("/login")
    pendingRequests=ServiceRequest.query.filter_by(professionalId=pid,status="pending",reqType="private").all()
    acceptedRequests=ServiceRequest.query.filter_by(professionalId=pid,status="accepted").all()
    closedRequests=ServiceRequest.query.filter_by(professionalId=pid,status="closed").all()
    return render_template("professionalDashboard.html",pendingRequests=pendingRequests,acceptedRequests=acceptedRequests,closedRequests=closedRequests,professionalName=session['username'])

@app.route("/professionalDashboard/acceptRequest/<int:requestId>")
def acceptRequest(requestId):
    if not session.get('isProfessional'):
        flash("Please login first !",'danger')
        return redirect("/login")
    serviceRequest=ServiceRequest.query.get_or_404(requestId)
    serviceRequest.status="accepted"
    db.session.commit()
    flash("Request accepted successfully !",'success')
    return redirect("/professionalDashboard")

@app.route("/professionalDashboard/rejectRequest/<int:requestId>")
def rejectRequest(requestId):
    if not session.get('isProfessional'):
        flash("Please login first !",'danger')
        return redirect("/login")
    serviceRequest=ServiceRequest.query.get_or_404(requestId)
    serviceRequest.status="rejected"
    db.session.commit()
    flash("Request rejected successfully !",'success')
    return redirect("/professionalDashboard")

@app.route("/professionalDashboard/summary", methods=["GET", "POST"])
def professionalSummary():
    if not session.get('isProfessional'):
        flash("Please login first !", 'danger')
        return redirect("/login")
    acceptedCount=ServiceRequest.query.filter_by(status="accepted").count()
    pendingCount=ServiceRequest.query.filter_by(status="pending").count()
    closedCount=ServiceRequest.query.filter_by(status="closed").count()
    rejectedCount=ServiceRequest.query.filter_by(status="rejected").count()
    img3=os.path.join(curr_dir,"static","images","img3.png")
    status=["Accepted","Pending","Closed","Rejected"]
    counts=[acceptedCount,pendingCount,closedCount,rejectedCount] 
    plt.clf()
    plt.figure(figsize=(10, 8))
    plt.pie(counts,labels=status,colors=["green","yellow","orange","red"],autopct='%1.1f%%')
    # plt.title("Number of requests by status")
    plt.savefig(img3,format="png")

    return render_template("professionalSummary.html",professionalName=session['username'],acceptedCount=acceptedCount,pendingCount=pendingCount,closedCount=closedCount,rejectedCount=rejectedCount)


#************************************************************************************************************************
@app.route("/customerRegister", methods=["GET","POST"])
def customerRegister():
    if request.method == "POST":
        username = request.form.get("username")
        password = generate_password_hash(request.form.get("password"))     
        email = request.form.get("email")
        address = request.form.get("address")
        pincode = request.form.get("pincode")
        user=Alluser.query.filter_by(username=username).first()
        if user:
            flash("Username already exists. Please choose a different username.",'danger')
            return redirect("/customerRegister")
        else:
            user=Alluser(username=username,password=password,email=email,address=address,pincode=pincode,isCustomer=True,isApproved=True)
            db.session.add(user)
            db.session.commit()
            flash("Customer Registration Successful !",'success')
            return redirect("/login")     
    return render_template("customerRegister.html")

@app.route("/customerDashboard", methods=["GET","POST"])
def customerDashboard():
    if not session.get('isCustomer'):
        flash("Please login first !",'danger')      
        return redirect("/customerRegister")
    customer=Alluser.query.filter_by(username=session["username"]).first()
    services=Services.query.join(Alluser).filter(Alluser.isApproved==True).all()
    serviceHistory=ServiceRequest.query.filter_by(customerId=customer.id).all()    
    return render_template("customerDashboard.html",services=services,serviceHistory=serviceHistory,customerName=session['username'])

@app.route("/customerDashboard/createRequest/<int:serviceId>", methods=["GET","POST"])
def createRequest(serviceId):
    if not session.get('isCustomer'):
        flash("Please login first !",'danger')      
        return redirect("/login")
    if request.method == "POST":
        professional=request.form.get('professional')
        description=request.form.get('description')
        pid=Alluser.query.filter_by(username=professional).first().id
        customer=Alluser.query.filter_by(username=session["username"]).first()
        serviceRequest=ServiceRequest(customerId=customer.id,professionalId=pid,serviceId=serviceId,description=description,status='pending',reqType='private')
        db.session.add(serviceRequest)
        db.session.commit()
        flash("Service Request created successfully !",'success')
        return redirect("/customerDashboard")
    service=Services.query.get_or_404(serviceId)
    professionals=Alluser.query.filter_by(isProfessional = True,isApproved=True,serviceId=serviceId).all()
    return render_template("createRequest.html",service=service,professionals=professionals,customerName=session['username'])

@app.route("/customerDashboard/editRequest/<int:serviceRequestId>", methods=["GET","POST"])    
def editRequest(serviceRequestId):
    if not session.get('isCustomer'):
        flash('Please login First','danger')
        return redirect('/login')
    serviceRequest=ServiceRequest.query.get_or_404(serviceRequestId)
    if request.method == "POST":
        description = request.form.get('description')
        serviceRequest.description = description
        db.session.commit()
        flash("Requested updated successfully",'success')
        return redirect("/customerDashboard")
    return render_template("editRequest.html",serviceRequest=serviceRequest)  

@app.route("/customerDashboard/deleteRequest/<int:serviceRequestId>", methods=["GET","POST"])    
def deleteRequest(serviceRequestId):
    if not session.get('isCustomer'):
        flash('Please login First','danger')
        return redirect('/login')
    serviceRequest = ServiceRequest.query.get_or_404(serviceRequestId)
    db.session.delete(serviceRequest)
    db.session.commit()
    flash("Request Deleted successfully",'success')
    return redirect("/customerDashboard")

@app.route("/customerDashboard/search" )     
def customerSearch():
    if not session.get('isCustomer'):
        flash('Please login First','danger')
        return redirect('/login')
    searchType=request.args.get('searchType')
    searchQuery=request.args.get('searchQuery')
    if searchQuery:

        if searchType=='pincode':
            services=Services.query.join(Alluser).filter(Alluser.isApproved==True,Alluser.pincode.like("%"+searchQuery+"%")).all()
        elif searchType=='serviceName':
            services=Services.query.filter(Services.serviceName.like("%"+searchQuery+"%")).all()
        elif searchType=='address':
            services=Services.query.join(Alluser).filter(Alluser.isApproved==True,Alluser.address.like("%"+searchQuery+"%")).all()

    else:
        services=Services.query.join(Alluser).filter(Alluser.isApproved==True).all()
    return render_template("customerSearch.html",services=services,customerName=session['username'])

@app.route("/customerDashboard/professionalProfile/<int:professionalId>")     
def professionalProfile(professionalId):
    if not session.get('isCustomer'):
        flash('Please login First','danger')
        return redirect('/login')
    newProfessional=Alluser.query.get_or_404(professionalId)
    reviews=ServiceRequest.query.filter_by(professionalId=professionalId,status='closed').all()
    return render_template("professionalProfile.html",newProfessional=newProfessional,reviews=reviews,customerName=session['username'])

@app.route("/customerDashboard/closeRequest/<int:requestId>",methods=["GET","POST"])
def closeRequest(requestId):
    if not session.get('isCustomer'):
        flash('Please login First','danger')
        return redirect('/login')
    
    serviceRequest=ServiceRequest.query.get_or_404(requestId)
    if not serviceRequest:
        flash("Request not found !",'danger')
        return redirect("/customerDashboard")
    
    if request.method == "POST":
        review = request.form.get('review')
        rating = request.form.get('rating')
        serviceRequest.status = 'closed'
        serviceRequest.ratingByCustomer = int(rating)
        serviceRequest.reviewByCustomer = review
        serviceRequest.dateClosed=datetime.now().date()

        profReviewUpdate=Alluser.query.get_or_404(serviceRequest.professionalId)
        temp=profReviewUpdate.ratingCount
        profReviewUpdate.ratingCount=temp+1
        #profReviewUpdate.averageRating = (profReviewUpdate.averageRating * (temp+1) + float(rating)) / (profReviewUpdate.ratingCount + 1)
        profReviewUpdate.averageRating = (profReviewUpdate.averageRating * temp + float(rating)) / (profReviewUpdate.ratingCount )
        

        db.session.commit()
        flash("Request closed successfully !",'success')
        return redirect("/customerDashboard")
   
    professional=serviceRequest.professional.username
    service=serviceRequest.service.serviceName
    return render_template("ratingReviews.html",professional=professional,service=service,requestId=requestId,customerName=session['username'])

@app.route("/customerDashboard/summary", methods=["GET", "POST"])
def customerSummary():
    if not session.get('isCustomer'):
        flash("Please login first !", 'danger')
        return redirect("/login")
    acceptedCount=ServiceRequest.query.filter_by(status="accepted").count()
    pendingCount=ServiceRequest.query.filter_by(status="pending").count()
    closedCount=ServiceRequest.query.filter_by(status="closed").count()
    rejectedCount=ServiceRequest.query.filter_by(status="rejected").count()
    img3=os.path.join(curr_dir,"static","images","img3.png")
    status=["Accepted","Pending","Closed","Rejected"]
    counts=[acceptedCount,pendingCount,closedCount,rejectedCount] 
    plt.clf()
    plt.figure(figsize=(10, 8))
    plt.pie(counts,labels=status,colors=["green","yellow","orange","red"],autopct='%1.1f%%')
    plt.savefig(img3,format="png")

    return render_template("customerSummary.html",customerName=session['username'],acceptedCount=acceptedCount,pendingCount=pendingCount,closedCount=closedCount,rejectedCount=rejectedCount)



#************************************************************************************************************************
@app.route("/logout")
def logout():
    session.pop('username', None)
    session.pop('isAdmin', None)
    session.pop('isProfessional', None)
    session.pop('isCustomer', None)
    flash("Logout Successful !",'success')
    return redirect(url_for('home'))

if __name__ == "__main__":
    app.run(debug=True)
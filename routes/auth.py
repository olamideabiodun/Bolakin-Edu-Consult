from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from models import db, User
from forms.auth_forms import LoginForm, ChangePasswordForm

auth = Blueprint('auth', __name__)

@auth.route('/login', methods=['GET', 'POST'])
def login():
    """User login page"""
    if current_user.is_authenticated:
        # Check if using default password
        if not current_user.password_changed:
            flash('Please change your default password for security reasons.', 'warning')
            return redirect(url_for('auth.change_password'))
        return redirect(url_for('admin.dashboard'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember_me.data)
            
            # Redirect to password change if using default password
            if not user.password_changed:
                flash('For security reasons, you must change your default password before proceeding.', 'warning')
                return redirect(url_for('auth.change_password'))
            
            next_page = request.args.get('next')
            
            # Redirect admin users to admin dashboard
            if user.is_admin:
                return redirect(next_page or url_for('admin.dashboard'))
            
            return redirect(next_page or url_for('main.index'))
        
        flash('Invalid username or password', 'danger')
    
    return render_template('auth/login.html', form=form)


@auth.route('/logout')
@login_required
def logout():
    """User logout"""
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('main.index'))


@auth.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    """Change user password"""
    form = ChangePasswordForm()
    
    # If user is using default password, show a warning
    default_password = not current_user.password_changed
    
    if form.validate_on_submit():
        if current_user.check_password(form.current_password.data):
            # Prevent setting the default password again
            if form.new_password.data == 'changeme123':
                flash('You cannot use the default password. Please choose a different password.', 'danger')
                return render_template('auth/change_password.html', form=form, default_password=default_password)
            
            current_user.set_password(form.new_password.data)
            current_user.password_changed = True  # Mark password as changed
            db.session.commit()
            
            flash('Your password has been updated.', 'success')
            
            # If this was a forced password change, redirect to dashboard
            if default_password:
                return redirect(url_for('admin.dashboard'))
            else:
                return redirect(url_for('admin.dashboard'))
        else:
            flash('Invalid current password.', 'danger')
    
    return render_template('auth/change_password.html', form=form, default_password=default_password)
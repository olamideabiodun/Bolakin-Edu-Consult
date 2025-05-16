from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SubmitField, SelectField, DateField
from wtforms.validators import DataRequired, Email, Optional, Length

class VisaRequestForm(FlaskForm):
    full_name = StringField('Full Name', validators=[DataRequired(), Length(max=150)])
    email = StringField('Email Address', validators=[DataRequired(), Email(), Length(max=150)])
    phone = StringField('Phone Number', validators=[DataRequired(), Length(max=20)])
    destination_country = StringField('Destination Country', validators=[DataRequired(), Length(max=100)])
    visa_type = SelectField('Visa Type', 
                            choices=[
                                ('', '-- Select Visa Type --'),
                                ('Tourist', 'Tourist Visa'),
                                ('Student', 'Student Visa'),
                                ('Work', 'Work Visa'),
                                ('Business', 'Business Visa'),
                                ('Family Reunion', 'Family Reunion Visa'),
                                ('Other', 'Other')
                            ], 
                            validators=[DataRequired()])
    other_visa_type = StringField('Specify Other Visa Type', validators=[Optional(), Length(max=100)]) # For when 'Other' is selected
    preferred_appointment_date = DateField('Preferred Appointment Date (Optional)', format='%Y-%m-%d', validators=[Optional()])
    message = TextAreaField('Additional Message (Optional)', validators=[Optional(), Length(max=5000)])
    submit = SubmitField('Submit Visa Request')

class UpdateVisaRequestStatusForm(FlaskForm):
    status = SelectField('Status', 
                         choices=[
                            ('Pending', 'Pending'),
                            ('In Review', 'In Review'),
                            ('Action Required', 'Action Required'),
                            ('Processed', 'Processed'),
                            ('Completed', 'Completed'),
                            ('Rejected', 'Rejected')
                         ],
                         validators=[DataRequired()])
    admin_notes = TextAreaField('Administrator Notes (Optional)', validators=[Optional(), Length(max=5000)])
    submit = SubmitField('Update Status')

class UpdateFlightBookingRequestStatusForm(FlaskForm):
    status = SelectField('Status', 
                         choices=[
                            ('Pending', 'Pending'),
                            ('Quotation Sent', 'Quotation Sent'),
                            ('Awaiting Payment', 'Awaiting Payment'),
                            ('Ticketed', 'Ticketed'),
                            ('Completed', 'Completed'),
                            ('Cancelled', 'Cancelled'),
                            ('On Hold', 'On Hold')
                         ],
                         validators=[DataRequired()])
    admin_notes = TextAreaField('Administrator Notes (Optional)', validators=[Optional(), Length(max=5000)])
    submit = SubmitField('Update Status')

class FlightBookingRequestForm(FlaskForm):
    full_name = StringField('Full Name', validators=[DataRequired(), Length(max=150)])
    email = StringField('Email Address', validators=[DataRequired(), Email(), Length(max=150)])
    phone = StringField('Phone Number', validators=[DataRequired(), Length(max=20)])
    
    trip_type = SelectField('Trip Type', 
                            choices=[
                                ('Round Trip', 'Round Trip'),
                                ('One Way', 'One Way')
                            ],
                            validators=[DataRequired()], default='Round Trip')
    
    departure_city = StringField('Departure City/Airport', validators=[DataRequired(), Length(max=100)])
    arrival_city = StringField('Arrival City/Airport', validators=[DataRequired(), Length(max=100)])
    departure_date = DateField('Departure Date', format='%Y-%m-%d', validators=[DataRequired()])
    return_date = DateField('Return Date (for Round Trip)', format='%Y-%m-%d', validators=[Optional()]) # Validated conditionally in route
    
    adults = SelectField('Adults (12+)', choices=[(i, str(i)) for i in range(1, 10)], coerce=int, default=1, validators=[DataRequired()])
    children = SelectField('Children (2-11)', choices=[(i, str(i)) for i in range(0, 10)], coerce=int, default=0, validators=[Optional()])
    infants = SelectField('Infants (Under 2)', choices=[(i, str(i)) for i in range(0, 5)], coerce=int, default=0, validators=[Optional()])
    
    cabin_class = SelectField('Cabin Class', 
                              choices=[
                                  ('Economy', 'Economy'),
                                  ('Premium Economy', 'Premium Economy'),
                                  ('Business', 'Business Class'),
                                  ('First', 'First Class')
                              ],
                              default='Economy', validators=[DataRequired()])
    flexible_dates = SelectField('Are your dates flexible?', 
                                choices=[
                                    (False, 'No, specific dates'), 
                                    (True, 'Yes, flexible by +/- 3 days')
                                ], coerce=lambda x: x == 'True', default=False, validators=[Optional()])

    message = TextAreaField('Additional Preferences or Message (Optional)', validators=[Optional(), Length(max=5000)])
    submit = SubmitField('Request Flight Booking')

class ProofOfFundsRequestForm(FlaskForm):
    full_name = StringField('Full Name', validators=[DataRequired(), Length(max=150)])
    email = StringField('Email Address', validators=[DataRequired(), Email(), Length(max=150)])
    phone = StringField('Phone Number', validators=[DataRequired(), Length(max=20)])
    
    service_type = SelectField('Type of Proof of Funds Needed', 
                               choices=[
                                   ('', '-- Select Service Type --'),
                                   ('Bank Statement Assistance', 'Bank Statement Assistance'),
                                   ('Sponsorship Letter Guidance', 'Sponsorship Letter Guidance'),
                                   ('Property Valuation Referral', 'Property Valuation Referral'),
                                   ('Investment Portfolio Review', 'Investment Portfolio Review'),
                                   ('Other', 'Other (Please specify in message)')
                               ],
                               validators=[DataRequired()])
    
    purpose = SelectField('Purpose of Proof of Funds',
                          choices=[
                              ('', '-- Select Purpose --'),
                              ('Study Permit / Student Visa', 'Study Permit / Student Visa'),
                              ('Visitor / Tourist Visa', 'Visitor / Tourist Visa'),
                              ('Permanent Residency Application', 'Permanent Residency Application'),
                              ('Business Investment', 'Business Investment'),
                              ('Personal Use', 'Personal Use'),
                              ('Other', 'Other (Please specify in message)')
                          ],
                          validators=[DataRequired()])
    
    destination_country = StringField('Destination Country (if applicable)', validators=[Optional(), Length(max=100)])
    amount_required = StringField('Approximate Amount Required (e.g., 15,000 CAD or 10,000,000 NGN)', validators=[Optional(), Length(max=100)])
    
    timeline = SelectField('Urgency / Timeline',
                         choices=[
                             ('', '-- Select Timeline --'),
                             ('Urgent (Within 1 week)', 'Urgent (Within 1 week)'),
                             ('Standard (2-4 weeks)', 'Standard (2-4 weeks)'),
                             ('Flexible (1 month+)', 'Flexible (1 month+)')
                         ],
                         validators=[Optional()])
    
    message = TextAreaField('Additional Details or Specific Requirements', validators=[Optional(), Length(max=5000)])
    submit = SubmitField('Submit Proof of Funds Request')

class UpdateProofOfFundsRequestStatusForm(FlaskForm):
    status = SelectField('Status', 
                         choices=[
                            ('Pending', 'Pending'),
                            ('Information Requested', 'Information Requested'),
                            ('Documents Submitted', 'Documents Submitted'),
                            ('In Review', 'In Review'),
                            ('Guidance Provided', 'Guidance Provided'),
                            ('Completed', 'Completed'),
                            ('On Hold', 'On Hold'),
                            ('Cancelled', 'Cancelled')
                         ],
                         validators=[DataRequired()])
    admin_notes = TextAreaField('Administrator Notes (Optional)', validators=[Optional(), Length(max=5000)])
    submit = SubmitField('Update Status')

class HolidayPackageRequestForm(FlaskForm):
    full_name = StringField('Full Name', validators=[DataRequired(), Length(max=150)])
    email = StringField('Email Address', validators=[DataRequired(), Email(), Length(max=150)])
    phone = StringField('Phone Number', validators=[DataRequired(), Length(max=20)])
    destination = StringField('Desired Destination(s)', validators=[DataRequired(), Length(max=200)], render_kw={"placeholder": "e.g., Dubai, Paris, Kenya Safari"})
    
    travel_dates_flexible = SelectField('Are your travel dates flexible?',
                                      choices=[
                                          (False, 'No, specific dates'),
                                          (True, 'Yes, my dates are flexible')
                                      ], coerce=lambda x: x == 'True', default=False, validators=[Optional()])
    preferred_start_date = DateField('Preferred Start Date', format='%Y-%m-%d', validators=[Optional()])
    preferred_end_date = DateField('Preferred End Date', format='%Y-%m-%d', validators=[Optional()])
    duration_days = StringField('Approximate Duration (e.g., 7 days, 2 weeks)', validators=[Optional(), Length(max=50)])

    num_adults = SelectField('Number of Adults (12+)', choices=[(i, str(i)) for i in range(1, 11)], coerce=int, default=1, validators=[DataRequired()])
    num_children = SelectField('Number of Children (0-11)', choices=[(i, str(i)) for i in range(0, 11)], coerce=int, default=0, validators=[Optional()])
    
    package_type = SelectField('Preferred Package Type',
                               choices=[
                                   ('', '-- Select Package Type --'),
                                   ('Luxury', 'Luxury'),
                                   ('Mid-Range', 'Mid-Range'),
                                   ('Budget-Friendly', 'Budget-Friendly'),
                                   ('Adventure', 'Adventure & Outdoors'),
                                   ('Family Fun', 'Family Fun'),
                                   ('Romantic Getaway', 'Romantic Getaway'),
                                   ('Cultural Immersion', 'Cultural Immersion'),
                                   ('Cruise', 'Cruise'),
                                   ('Custom', 'Custom (Describe below)')
                               ],
                               validators=[Optional()])
    
    interests = TextAreaField('Interests and Activities (Optional)', validators=[Optional(), Length(max=2000)], render_kw={"placeholder": "e.g., Beaches, Museums, Hiking, Shopping, Nightlife"})
    
    budget_preference = SelectField('Budget Preference (Per Person, Optional)',
                                  choices=[
                                      ('', '-- Select Budget Range --'),
                                      ('Under $500', 'Under $500'),
                                      ('$500 - $1000', '$500 - $1,000'),
                                      ('$1000 - $2000', '$1,000 - $2,000'),
                                      ('$2000 - $5000', '$2,000 - $5,000'),
                                      ('$5000+', '$5,000+'),
                                      ('Flexible', 'Flexible / Not Sure')
                                  ],
                                  validators=[Optional()])
    
    message = TextAreaField('Additional Information or Specific Requests', validators=[Optional(), Length(max=5000)], render_kw={"placeholder": "Tell us anything else to help us plan your perfect holiday!"})
    submit = SubmitField('Request Holiday Package')

class UpdateHolidayPackageRequestStatusForm(FlaskForm):
    status = SelectField('Status', 
                         choices=[
                            ('Pending', 'Pending'),
                            ('Consultation Scheduled', 'Consultation Scheduled'),
                            ('Itinerary Proposed', 'Itinerary Proposed'),
                            ('Package Quoted', 'Package Quoted'),
                            ('Awaiting Payment', 'Awaiting Payment'),
                            ('Booked & Confirmed', 'Booked & Confirmed'),
                            ('Travel Completed', 'Travel Completed'),
                            ('On Hold', 'On Hold'),
                            ('Cancelled', 'Cancelled')
                         ],
                         validators=[DataRequired()])
    admin_notes = TextAreaField('Administrator Notes (Optional)', validators=[Optional(), Length(max=5000)])
    submit = SubmitField('Update Status')

class HotelAccommodationRequestForm(FlaskForm):
    full_name = StringField('Full Name', validators=[DataRequired(), Length(max=150)])
    email = StringField('Email Address', validators=[DataRequired(), Email(), Length(max=150)])
    phone = StringField('Phone Number', validators=[DataRequired(), Length(max=20)])
    
    destination_city_hotel = StringField('Destination City / Hotel Name (if known)', validators=[DataRequired(), Length(max=150)], render_kw={"placeholder": "e.g., Paris, France or Hilton Times Square"})
    check_in_date = DateField('Check-in Date', format='%Y-%m-%d', validators=[DataRequired()])
    check_out_date = DateField('Check-out Date', format='%Y-%m-%d', validators=[DataRequired()])
    
    num_adults = SelectField('Adults (12+)', choices=[(i, str(i)) for i in range(1, 11)], coerce=int, default=1, validators=[DataRequired()])
    num_children = SelectField('Children (0-11)', choices=[(i, str(i)) for i in range(0, 11)], coerce=int, default=0, validators=[Optional()])
    num_rooms = SelectField('Number of Rooms', choices=[(i, str(i)) for i in range(1, 6)], coerce=int, default=1, validators=[DataRequired()])
    
    room_type_preference = SelectField('Preferred Room Type (Optional)',
                                     choices=[
                                         ('', '-- Any Room Type --'),
                                         ('Standard', 'Standard'),
                                         ('Deluxe', 'Deluxe'),
                                         ('Suite', 'Suite'),
                                         ('Family Room', 'Family Room'),
                                         ('Connecting Rooms', 'Connecting Rooms'),
                                         ('Room with View', 'Room with View')
                                     ],
                                     validators=[Optional()])
    
    hotel_preferences = TextAreaField('Hotel Preferences (Optional)', validators=[Optional(), Length(max=2000)], render_kw={"placeholder": "e.g., 4-star or 5-star, near city center, specific amenities like pool, gym, breakfast included"})
    budget_per_night = StringField('Budget Per Night (Optional)', validators=[Optional(), Length(max=100)], render_kw={"placeholder": "e.g., $100-$150 USD, or 50,000 NGN"})
    special_requests = TextAreaField('Special Requests (Optional)', validators=[Optional(), Length(max=2000)], render_kw={"placeholder": "e.g., Early check-in, late check-out, specific dietary needs, accessibility requirements"})
    
    submit = SubmitField('Request Hotel Booking')

class UpdateHotelAccommodationRequestStatusForm(FlaskForm):
    status = SelectField('Status', 
                         choices=[
                            ('Pending', 'Pending'),
                            ('Options Sent', 'Options Sent'),
                            ('Awaiting Confirmation', 'Awaiting Confirmation'),
                            ('Booked & Confirmed', 'Booked & Confirmed'),
                            ('Stay Completed', 'Stay Completed'),
                            ('On Hold', 'On Hold'),
                            ('Cancelled', 'Cancelled')
                         ],
                         validators=[DataRequired()])
    admin_notes = TextAreaField('Administrator Notes (Optional)', validators=[Optional(), Length(max=5000)])
    submit = SubmitField('Update Status') 
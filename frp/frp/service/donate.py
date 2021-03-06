from random import randint
from flask import render_template
from .. import app
from ..models import (db, Donation, admin_user)
from flask_user import current_user
from string import Template
from string import split
from ..views.ccavutil import encrypt,decrypt
import threading

accessCode = app.config.get('CCAVENUE_ACCESS_CODE')
workingKey = app.config.get('CCAVENUE_WORKING_KEY')

def donation_validate(donation_id):
  donation = Donation.query.get(int(donation_id))
  if donation.confirmation == None:
      db.session.delete(donation)
      try:
        db.session.commit()
      except Exception as e:
        app.logger.warning('Unable to delete invalid donation')
        app.logger.warning(e)

def create_donation(form, campaign):
  amount = form.amount_choice.data
  if not amount:
    amount = form.customize_amount.data

  donor = current_user 
  
  donation = Donation(amount=amount, 
          donor=donor, 
          first_name=form.first_name.data,
          last_name=form.last_name.data,
          campaign=campaign, 
          state=form.state.data, 
          city=form.city.data, 
          identification=form.pan_number.data,
          identification_type="Pan Card",
          tax_exemption_certificate=(True if form.tax_exemption_certificate.data == "True" else False),
          ann_choice=(True if form.ann_choice.data == "True" else False))
  db.session.add(donation)
  try:
    db.session.commit()
  except Exception as e:
    app.logger.warning('Unable to save')
    app.logger.warning(e)
    db.session.rollback()
    return {'error': True, 'exc': e}
  # Function "donation_validate will be called after 600 seconds that is 10 minutes 
  threading.Timer(600,donation_validate,[donation.id]).start()
  return {'error': False,
          'donation': donation}

def ccavRequest(form, donation):
  p_merchant_id = "37848"
  p_order_id = str(donation.id)
  p_currency = 'INR'
  p_amount = str(donation.amount)
  p_redirect_url = "https://donateabook.org.in/billing/success"
  p_cancel_url = "https://donateabook.org.in/billing/failure"
  p_language = 'EN'
  p_integration_type = "iframe_normal"
  
  p_billing_name = form.first_name.data + ' ' + form.last_name.data
  p_billing_address = form.address.data
  p_billing_city = form.city.data
  p_billing_state = form.state.data
  p_billing_zip = form.pin.data
  p_billing_country = 'India'
  p_billing_tel = form.phone_number.data
  p_billing_email = form.email.data

  merchant_data='merchant_id=' + p_merchant_id + '&' + 'order_id=' + p_order_id + '&' + 'currency=' + p_currency + '&' + 'amount=' + p_amount + '&' + 'redirect_url=' + p_redirect_url + '&' + 'cancel_url=' + p_cancel_url + '&' + 'language=' + p_language + '&' + 'integration_type=' + p_integration_type + '&' + 'billing_name=' + p_billing_name + '&' + 'billing_address=' + p_billing_address + '&' + 'billing_city=' + p_billing_city + '&' + 'billing_state=' + p_billing_state + '&' + 'billing_zip=' + p_billing_zip + '&' + 'billing_country=' + p_billing_country + '&' + 'billing_tel=' + p_billing_tel + '&' + 'billing_email=' + p_billing_email + '&'
  app.logger.warning('merchant data = ' + merchant_data)
	
  encryption = encrypt(merchant_data,workingKey)

  html = '''\
<html>
<head>
	<title>Sub-merchant checkout page</title>
	<script src="http://ajax.googleapis.com/ajax/libs/jquery/1.10.2/jquery.min.js"></script>
</head>
<body>
    <center>
	<!-- width required mininmum 482px -->
       	<iframe  width="482" height="500" scrolling="No" frameborder="0"  id="paymentFrame" src="https://secure.ccavenue.com/transaction/transaction.do?command=initiateTransaction&merchant_id=$mid&encRequest=$encReq&access_code=$xscode">
	  	</iframe>
	</center>
	
	<script type="text/javascript">
    	$(document).ready(function(){
    		$('iframe#paymentFrame').load(function() {
				 window.addEventListener('message', function(e) {
			    	 $("#paymentFrame").css("height",e.data['newHeight']+'px'); 	 
			 	 }, false);
			 }); 
    	});
	</script>
  </body>
</html>
'''
  fin = Template(html).safe_substitute(mid=p_merchant_id,encReq=encryption,xscode=accessCode)
		
  return fin	

def ccavResponse(encresp):
  plainText = decrypt(encresp, workingKey)	
  app.logger.warning("Response = " + plainText)
  args = split(plainText, '&')
  args = map(lambda x: split(x, '='), args)
  donation_id = 0
  tracking_id = 0
  
  for arg in args:
  #  app.logger.warning('Donation ' + arg[0] + ' = ' + arg[1])
    if (arg[0] == 'order_id'):
      donation_id = arg[1]
    if (arg[0] == 'tracking_id'):
      tracking_id = arg[1]
    if (arg[0] == 'order_status'):
      order_status = arg[1]

  return (donation_id, tracking_id, order_status)
   

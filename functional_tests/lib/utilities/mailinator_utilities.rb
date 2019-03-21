require 'mailinator'
require 'ithaka_credentials'

class MailinatorUtilities

  def initialize
    mailinator_token = ITHAKA::Credentials.get_cred('mailinator')['token']
    Mailinator.configure do |config|
      config.token = mailinator_token
    end
  end

  def get_inbox(user)
    Mailinator::Inbox.get(user)
  end

  def get_first_message(user)
    inbox = get_inbox(user)
    if inbox.messages.first.nil?
      puts "There is no message to get from Inbox of #{user}"
    else
      inbox.messages.first.download
    end
  end

  def delete_first_message(user)
    inbox = get_inbox(user)
    if inbox.messages.first.nil?
      puts "There is no message to delete from Inbox of #{user}"
    else
      inbox.messages.first.delete
    end
  end

  def delete_all_messages(user)
    i = 0
    while get_inbox(user).messages.first != nil do
      i += 1
      delete_first_message(user)
      sleep 1
      raise 'Problem in deleting mails in mailinator, not expect to delete over 20 mails' if i > 20
    end
  end

end





require 'json'
require 'mechanize'

class JSONParser<Mechanize::File
   attr_reader :json
  def initialize(uri=nil,response=nil,body=nil,code=nil)
    super(uri,response,body,code)
    begin
      @json=JSON.parse(body, :symbolize_names => true)
    rescue =>_
      @json = body
    end
  end

end
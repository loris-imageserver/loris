module ITHAKA
  module OS
    require 'rbconfig'
    def self.host_os
      RbConfig::CONFIG['host_os']
    end

    def self.windows?
      (/cygwin|mswin|mingw|bccwin|wince|emx|windows/ =~ host_os) != nil
    end

    def self.mac?
      (/darwin/ =~ host_os) != nil
    end

    def self.linux?
      (/linux|arch/ =~ host_os) != nil
    end
  end
end
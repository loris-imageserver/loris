module ITHAKA
  module XLS

    def self.update_spreadsheet(original_filename, original_value, new_value)
      workbook = Spreadsheet.open(DOWNLOAD_DIR+original_filename)
      sheet1 = workbook.worksheet(0)
      sheet1.rows.each_with_index do |row, index|
        data_row = row.map {|c| c == original_value ? c = new_value : c}
        sheet1.delete_row(index)
        sheet1.insert_row(index, data_row)
      end
      File.delete(DOWNLOAD_DIR+original_filename)
      workbook.write(DATA_FILE_LOCAL_DIR+original_filename)
      File.expand_path(DATA_FILE_LOCAL_DIR+original_filename)
    end

    def self.compare_excels(excel_file1, excel_file2)

      sheet1 = self.readFirstSheet excel_file1
      sheet2 = self.readFirstSheet excel_file2

      for row in 0 ... sheet1.count
        for col in 0 ... sheet1.row(row).size
          if sheet1.rows[row][col] != sheet2.rows[row][col]
            return false
          end
        end
      end
      return true
    end

    def self.update_spreadsheet_multiple_values(input_file_path, original_values, new_values, output_file_path)
      workbook = Spreadsheet.open(input_file_path)
      sheet1 = workbook.worksheet(0)
      sheet1.rows.each_with_index do |row, index|

        data_row = row.map {|x| x}
        for val_index in 0 ... original_values.count
          original_value = original_values[val_index]
          new_value = new_values[val_index]
          data_row = data_row.map {|c| c == original_value ? c = new_value : c}
        end
        sheet1.delete_row(index)
        sheet1.insert_row(index, data_row)
      end
      workbook.write(output_file_path)
      workbook.io.close
    end

    def self.get_total_row_count(filename)
      worksheet = Spreadsheet.open(DOWNLOAD_DIR+filename).worksheet(0)
      worksheet.last_row_index
    end

    def self.readFirstSheet(response)
      worksheet = Spreadsheet.open(response).worksheet(0)
      worksheet
    end
  end

  module S3Utilities
# Simple helper method that handles the s3 file manipulation(only contains methods used at the moment)
#The get_bucket_files returns a list of files in the Default bucket
#
# get_s3_data_file will download the file to the local s3data directory and return the full path.
#
    def self.get_s3_data_file(data_file_name, options = {:folder => ''})
      bucket = S3OBJ.bucket(S3_DATA_FILE_BUCKET)
      local_data_file_path = "#{DATA_FILE_LOCAL_DIR}#{data_file_name}"
      unless File.exist?(local_data_file_path)
        if options[:folder] == ''
          bucket.object(data_file_name).download_file(local_data_file_path)
        else
          bucket.object(options[:folder]+data_file_name).download_file(local_data_file_path)
        end
      end
      File.expand_path(local_data_file_path)
    end


    def self.upload_to_s3(bucket, local_source_path, filename, options = {:folder => ''})
      s3_obj = Aws::S3::Resource.new(region: 'us-east-1')
      s3_data_file_bucket = bucket
      bucket = s3_obj.bucket(s3_data_file_bucket)
      if options[:folder] == ''
        bucket.object(filename).upload_file(local_source_path+filename)
      else
        bucket.object(options[:folder]+filename).upload_file(local_source_path+filename)
      end
    end

    def self.s3_data_file(filename, options = {:folder => ''})
      bucket = S3OBJ.bucket(S3_DATA_FILE_BUCKET)
      if options[:folder] == ''
        bucket.object(filename)
      else
        bucket.object(options[:folder]+filename)
      end

    end


  end
end
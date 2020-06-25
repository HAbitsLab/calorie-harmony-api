$(document).ready(function() {
    $('#upload_acti').submit(function(event){
        event.preventDefault();
        console.log("Loading data")
        var formdata = new FormData();
        var files = $('#file')[0].files[0];
        console.log(files)
        formdata.append('file',files);
        console.log(formdata)
        $.ajax({
            url: '/actifile/',
            type: 'POST',
            data: formdata,
            contentType: false,
            processData: false,
            success: function(data, textStatus, jqXHR) {
                console.log(data)
                var Time = (data.data.Time);
                var Mets = (data.data["ActiGraph VM3 Estimation (MET)"]);
                console.log(Mets)

                var trHTML = '';
                $.each(Time, function (i, item) {
    
                    trHTML += '<tr><td>' + Time[i] + '</td><td>' + Mets[i] + '</td></tr>';
                });
                
                $('#acti_met_table').append(trHTML);              
            }
        });
    });

    var file_list = [];

    $('input:file[multiple]').change(
        function(e){
            console.log(e.currentTarget.files);
            var numFiles = e.currentTarget.files.length;
                for (i=0;i<numFiles;i++){
                    fileSize = parseInt(e.currentTarget.files[i].size, 10)/1024;
                    filesize = Math.round(fileSize);
                    file_list.push(e.currentTarget.files[i]);
                    $('<li />').text(e.currentTarget.files[i].name).appendTo($('#output'));
                    $('<span />').addClass('filesize').text('(' + filesize + 'kb)').appendTo($('#output li:last'));
                }
        });

    $('#upload_wrist').submit(function(event){
        event.preventDefault();
        console.log("Loading wrist data")
        var formdata = new FormData();
        $.each(file_list, function(i, file) {
            console.log(file)
            formdata.append('files', file);
            
        });
        console.log(formdata)
        $.ajax({
            url: '/wristfiles/',
            type: 'POST',
            data: formdata,
            contentType: false,
            processData: false,
            success: function(data, textStatus, jqXHR) {
                console.log(data)
                var Time = (data.data.Time);
                var Mets = (data.data["Wrist Estimation (MET)"]);
                // console.log(Mets)

                var trHTML = '';
                $.each(Time, function (i, item) {

                     trHTML += '<tr><td>' + Time[i] + '</td><td>' + Mets[i] + '</td></tr>';
                });
                
                $('#wrist_met_table').append(trHTML);              
            }
        });
    });
});



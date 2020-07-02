var updateTableInterval = null

$(document).ready(function() {
    $('.demo.menu .item').tab({history:false}); //tab functioning
    $('#upload_acti').submit(function(event){
        event.preventDefault();
        console.log("Loading data")
        var formdata = new FormData();
        var files = $('#file')[0].files[0];
        console.log(files)
        formdata.append('file',files);
        console.log(formdata)

        updateTableInterval = setInterval(function() {
            updateActi()
          }, 1000);
        $('#acti-files').append('<div id="acti_loading" class="ui active inverted dimmer"><div class="ui large text loader">Loading</div></div>')
        
        $.ajax({
            url: '/actifile/',
            type: 'POST',
            data: formdata,
            contentType: false,
            processData: false,
            success: function(data, textStatus, jqXHR) {
                console.log(data) 
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

        updateTableInterval = setInterval(function() {
            updateWrist()
          }, 5000);
        $('#wrist-files').append('<div id="wrist_loading" class="ui active inverted dimmer"><div class="ui large text loader">Loading</div></div>')
       
        $.ajax({
            url: '/wristfiles/',
            type: 'POST',
            data: formdata,
            contentType: false,
            processData: false,
            success: function(data, textStatus, jqXHR) {
                console.log(data)
            }
        });
    });   
});



function updateActi() {
    var acti_tbl = document.getElementById('acti_met_table');
    if (acti_tbl.rows.length < 2) {
        console.log("acti table empty")
        $("#acti-div").load(window.location.href + " #acti-div" );
        return false;
    } else {
        console.log("acti table not empty table")
        removeActiLoader();    
        clearInterval(updateTableInterval);
    }
}

function updateWrist() {
    var wrist_tbl = document.getElementById('wrist_met_table');
    if (wrist_tbl.rows.length < 2) {
        console.log("wrist table empty")
        $("#wrist-div").load(window.location.href + " #wrist-div" );
        return false;
    } else {
        console.log("wrist table not empty table")
        removeWristLoader();    
        clearInterval(updateTableInterval);
    }
}

function removeActiLoader(){
    $( "#acti_loading" ).fadeOut(500, function() {
    // fadeOut complete. Remove the loading div
    $( "#acti_loading" ).remove(); //makes page more lightweight 
});  
}

function removeWristLoader(){
    $( "#wrist_loading" ).fadeOut(500, function() {
    // fadeOut complete. Remove the loading div
    $( "#wrist_loading" ).remove(); //makes page more lightweight 
});  
}

function plot_data(){
    console.log("plotting data")
    $.ajax({
        url: '/plot/',
        type: 'POST',
        success: function(data, textStatus, jqXHR) {
            console.log(data)
             $('#plotdiv1').html(data["plot1"]);
             $('#plotdiv2').html(data["plot2"]);          
        }
    });
}

function clear_data(){
    console.log("clearing data")
    $.ajax({
        url: '/clear/',
        type: 'POST',
        success: function(data, textStatus, jqXHR) {
            console.log(data)
            $("#acti-div").load(window.location.href + " #acti-div" );
            $("#wrist-div").load(window.location.href + " #wrist-div" );
            return false;    
        }
    });
    
}


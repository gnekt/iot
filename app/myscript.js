var pick_image=0;
var mode = false;
var pump_state = false;
var is_full=1;
//GESTORE EVENTI INVIATI DALLA BOARD
function event_callback(event) {
    switch (event.payload.type){
        case 1:
            change_fotoval(event.payload.value);
        break;

        case 2:
            change_hum(event.payload.value);
        break;
            
        case 3:
            change_fillfactor(event.payload.value);
        break;

        case 4:
            change_temp(event.payload.value);
        break;

        case 5:
            change_soil_hum(event.payload.value);
        break;  

        case 6:
            state_light(event.payload.value);
        break;
        
        case 7:
            state_pump(event.payload.value);
        break;

        case 8:
            callback_plant(event.payload.value);
        break;

        default:
            error_sender("refused request, maybe it's not present!")
        break;   
    }

}
//EVENTO 1 CAMBIO VALORE SENSORE LUMINOSITà
function change_fotoval(randPercent){
    //Generic column color
    var color = '#90A4AE';
    
    if(randPercent >= 2800){
      color = '#00E676';
      randPercent=100;
    }
    else if(randPercent < 2800 && randPercent >= 2200){
      color = '#81C784';
      randPercent = 90;
    }
    else if (randPercent < 2200 && randPercent >= 1800){
      color = '#FFEB3B';
      randPercent=70;
    }
    else if (randPercent < 1800 && randPercent >= 1200){
      color = '#FF9800';
      randPercent=40;
    }
    else if (randPercent < 1200 && randPercent >= 600){
        color = '#FF9800';
        randPercent=40;
    }
    else if (randPercent < 600 && randPercent >= 0){
      color = '#FF3D00';
      randPercent=10;
    }
    
    $('.column').css({background: color});
    
    $('.column').animate({
      width: randPercent+'%',
    });
}

//EVENTO 2 CAMBIO LIVELLO UMIDITà AMBIENTE
function change_hum(value){
    document.getElementById("umidita_ambiente").className = "c100 p"+value+" green";
    document.getElementById("span_ambiente").innerHTML =""+value+"%";
}

//EVENTO 3 CAMBIAMENTO DI STATO DEL SERBATORIO
function change_fillfactor(value){
    if(value==0){
        $('#allarme').css('animation','');
        is_full=1;
    }
    else if(value == 1) {
        $('#allarme').css('animation','blink 1s infinite');
        is_full =0;
    }
}

//EVENTO 4 CAMBIO TEMPERATURA
function  change_temp(value){
    $('#grad_text').text(value+'°c')
}

//EVENTO 5 CAMBIO UMIDITà TERRENO
function change_soil_hum(value){
    if(value < 1 || value > 99 ){
        alert("PROBLEMS WITH THE HUMIDITY SENSOR, CHECK ITS POSITION!");
    }else{
    document.getElementById("umidita_terreno").className = "c100 p"+value+" orange";
    document.getElementById("span_terreno").innerHTML = ""+value+"%";
    }
}

//EVENTO 6 CAMBIO STATO LUCE
function state_light(value){
    if (value == 1){
        $('#off').css('z-index','0');
        $('#on').css('z-index','1');
    }
    if (value == 0){
        $('#on').css('z-index','0');
        $('#off').css('z-index','1');
    }
}

//EVENTO 7 CAMBIO STATO IRRIGAZIONE
function state_pump(value){
    if(value == 1){
        $('#annaffia').css('animation','blink 1s infinite');
    }
    else{
        $('#annaffia').css('animation','');
    }
    pump_state = value;
}

//LUCE ON
function turn_on_light(){
    event_sender(2,1);
}

//LUCE OFF
function turn_off_light(){
    event_sender(2,0);
}

//GESTORE INVIO EVENTI
function event_sender(cod_invio,value){
    Z.call('event',[parseInt(cod_invio,10),parseInt(value,10)]);
}

//GESTORE RICEZIONE RISPOSTA A SEGUITO DI UNA DOMANDA ALLA SCHEDA
function callback_plant(value){
    if(value == 1){
        location.href="plant-home.html";
    }
}



//INVIO CAMBIO MODALITA 
function manual_mode_switch(){
    console.log(mode);
    if(!mode){
        mode_sender = 1;
    }else{
        mode_sender = 0;
    }
    console.log(mode_sender);
    event_sender(99,mode_sender);
    mode = !mode;
    if(mode_sender == 1){
        alert("  CAUTION!! CAUTION!! IN AUTOMATIC MODE THE CONTROLS ON ALL THE SENSORS ARE DISABLED");
        $('#off').attr('onclick','turn_on_light()');
       $('#on').attr('onclick','turn_off_light()');
        $('#annaffia').css('opacity','1');
        $('#annaffia').attr('onclick','turn_pump()');
    }
    else{
        $('#off').attr('onclick','');
        $('#on').attr('onclick','');
        $('#annaffia').attr('onclick','');
        $('#annaffia').css('opacity','0');
    }
}

// AVVIO POMPA MANUALE
 function turn_pump(){
     if(!pump_state){
         if(is_full==0){
             alert("YOU CANNOT WATERING, EMPTY TANK!");
         }else{
         value = 1;
         }
     }else{
         value = 0;
     }
     console.log(mode_sender);
     event_sender(3,value);
     pump_state = !pump_state;
 }


//GESTORE INVIO ERRORI
function error_sender(error_string){
    Z.call('error',error_string);
}


function online_notify(event){
    alert(event.payload.text);
}

//FUNZIONE CHIAMATA ALLO STATO DI ONLINE DA PARTE DEL DEVICE ZERYNTH
function online_callback() {
    $('#title').css("animation","");
    $('#title').css("animation","online 3s infinite");
}

//FUNZIONE CHIAMATA ALLO STATO DI OFFLINE DA PARTE DEL DEVICE ZERYNTH
function offline_callback() {
    $('#title').css("animation","");
    $('#title').css("animation","offline 3s infinite");
}



// This is an initialization function that will be called
// after the page is loaded.
function initialize() {
    Z.init({
        on_event: event_callback,
        on_connected: online_callback,
        on_disconnected: offline_callback,
        on_notify : online_notify
    });
    
    $('#on').css('z-index','0');
    $('#off').css('z-index','1');
    $('#annaffia').css('opacity','0');
}

function reload(){
    event_sender(4,1);
    $('#reload').css('animation','rotate 2s ');
    setTimeout(function(){ $('#reload').css('animation',''); }, 2000);
}


function init(){
    Z.init({
        on_event: event_callback,
        on_connected: online_callback,
        on_disconnected: offline_callback,
        on_notify : online_notify
    });

}
function is_saved(){
    event_sender(5,1);
}





//imagepicker
function picked_image(id){
    i=1;
    while(i<4){
        console.log("test");
         if(i==id){
           $('#img'+id).css("animation","selected 1s forwards");
           pick_image = id;
         }else{
           $('#img'+i).css("animation","unselected 1s forwards");   
         }
    i++;
    }
    $('#confirm_button').removeAttr('disabled');
}

function send_type_plant(){
    console.log(pick_image);
    event_sender(1,pick_image);
}


//JS FOR STATS PAGE

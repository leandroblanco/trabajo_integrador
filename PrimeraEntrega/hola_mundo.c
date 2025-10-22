void detectarIntT2() org 0x0020  {
    IFS0bits.T2IF = 0;  // Borrar bandera de interrupción T2

    ADCON1bits.DONE = 0;  // Antes de pedir una muestra ponemos en cero
    ADCON1bits.SAMP = 1;  // Pedimos una muestra

    asm nop;

    ADCON1bits.SAMP = 0;  // Pedimos que retenga la muestra

}

void config_puertos()  {
    // Configurar RB0 como salida
    TRISBbits.TRISB0 = 0;

    TRISBbits.TRISB2 = 1;
    TRISBbits.TRISB3 = 0;
    TRISBbits.TRISB4 = 0;
    TRISBbits.TRISB5 = 0;
    TRISBbits.TRISB6 = 0;
    TRISBbits.TRISB7 = 0;
    TRISBbits.TRISB8 = 0;
    TRISBbits.TRISB9 = 0;
    TRISBbits.TRISB10 = 0;
}



void config_timer2()  {
    // Configurar Timer2
    T2CON = 0x0000;     // Timer apagado, configuración por defecto

    PR2 = 39062;         // Periodo del timer volver 2500

    T2CONbits.TCKPS = 0b10;  // Prescaler 1:1 (0b00)   actual 1:64
    T2CONbits.TON = 1;       // Encender Timer2

    // Habilitar interrupciones
    IEC0bits.T2IE = 1;       // Habilitar interrupción de Timer2
}



void config_adc()  {
    ADPCFG = 0xFFFB; // Elije la entrada analógica a convertir en este caso AN2.
    // Con cero se indica entrada analógica y con 1 sigue siendo entrada digital.

    ADCON1bits.ADON = 0;  // ADC Apagado por ahora
    ADCON1bits.ADSIDL = 1;  // No trabaja en modo idle
    ADCON1bits.FORM = 0b00;  // Formato de salida entero
    // Para tomar muestras en forma manual. Porque lo vamos a controlar con timer2
    ADCON1bits.SSRC = 0b000;
    // Adquiere muestra cuando el SAMP se pone en 1. SAMP lo controlamos desde el Timer2.
    ADCON1bits.ASAM = 0;

    ADCON2bits.VCFG = 0b000;  // Referencia con AVdd y AVss
    ADCON2bits.SMPI = 0b0000;  // Lanza interrupción luego de tomar n muestras.
    // Con SMPI=0b0 -> 1 muestra ; Con SMPI=0b1 -> 2 muestras ; Con SMPI=0b10 -> 3 muestras ; etc.

    // AD1CON3 no se usa ya que tenemos deshabilitado el cálculo del muestreo con ADCS etc.

    // Muestreo la entrada analógica AN2 contra el nivel de AVss (AN0 es S/H+ y AVss es S/H-)
    ADCHS = 0b0010;

    ADCON1bits.ADON = 1;// Habilitamos el A/D
}

void interrupcionADC() org 0x002A {
    unsigned int valorADC = ADCBUF0;
    char txt[6];
    int nivel = valorADC / 512; // 4096 / 512 = 128 por nivel
    LATBbits.LATB0 = !LATBbits.LATB0;

    // Apagar todos los LEDs
    LATBbits.LATB3 = 0;
    LATBbits.LATB4 = 0;
    LATBbits.LATB5 = 0;
    LATBbits.LATB6 = 0;
    LATBbits.LATB7 = 0;
    LATBbits.LATB8 = 0;
    LATBbits.LATB9 = 0;
    LATBbits.LATB10 = 0;

    // Encender según el nivel
    if (nivel >= 1) LATBbits.LATB3 = 1;
    if (nivel >= 2) LATBbits.LATB4 = 1;
    if (nivel >= 3) LATBbits.LATB5 = 1;
    if (nivel >= 4) LATBbits.LATB6 = 1;
    if (nivel >= 5) LATBbits.LATB7 = 1;
    if (nivel >= 6) LATBbits.LATB8 = 1;
    if (nivel >= 7) LATBbits.LATB9 = 1;
    if (nivel >= 8) LATBbits.LATB10 = 1;

    IFS0bits.ADIF = 0; // Borrar bandera de interrupción ADC

    // Enviar valor ADC por UART

   // WordToStr(nivel, txt);
    UART1_Write(nivel);
    //UART1_Write(13);
    //UART1_Write(10);
}


int main() {

    // --- UART1 a 9600 baudios ---
    UART1_Init(9600);            // usa clock del proyecto
    Delay_ms(100);               // breve estabilización

    config_puertos();
    config_timer2();

    // Configuramos el módulo ADC
    config_adc();

    IEC0bits.ADIE = 1;  // Habilitamos interrupción del A/D

    while (1) {
        // Bucle principal vacío, todo se maneja por interrupciones
    }

    return 0;
}

// dsPIC30F4013
// Placa Easy dsPIC 
// Entrada analogica AN8 - VRef es AVdd y AVss -
// Detecta las frecuencias 100 Hz, 200 Hz, 300 Hz, ..., 6300 Hz
// Publica el resultado en binario en los puertos RB0-RB5 (valores desde 1 al 63)

const unsigned long CANT_MUESTRAS = 128;  // 128 pares de valores [Re, Im]
const unsigned long FREC_MUESTREO  = 12800;  // Frecuencia de muestreo.

unsigned Samples[ CANT_MUESTRAS * 2 ];  // Capacidad para 256. Porque son 128 pares

// La funcion FFT requiere que las muestras se almacenen en el bloque de datos Y.
// Este bloque de memoria es una caracteristica de los dsPIC que permite realizar
// operaciones en una sola instruccion, lo que aumenta la velocidad de calculo.
ydata unsigned InputSamples[ CANT_MUESTRAS * 2 ];

// Almacena la frecuencia con mayor potencia en la senal de entrada
unsigned freq = 0;
unsigned freq_old = 0;  // Para almacenar la frecuencia detectada anteriormente. Para ver si se detecto una nueva o no.

// Es un indice para llevar la cuenta de cuantas muestras vamos guardando en Samples.
unsigned globali = 0;

// Bandera para saber si ya se encuentra listo el procesamiento FFT para mostrar el resultado.
char listo = 0;

// Para almacenar lo que se lee por el UART
char uart_rd;
// Para almacenar lo que se escribe a la UART
char uart_wr[ 7 ];


// Para almacenar los valores de cada una de las frecuencias
char magnitudFrecuencias[ CANT_MUESTRAS / 2 ];


void configuracionADC()  {
    ADPCFG = 0b01111111;  // elegimos AN7 como entrada para muestras
    ADCHS = 0b0111; // usamos AN7 para recibir las muestras en el ADC
    ADCON1bits.SSRC = 0b111; //  Internal counter ends sampling and starts conversion (auto convert)
    ADCON1bits.FORM = 0b11;  // Signed Fractional (DOUT = sddd dddd dd00 0000)
    ADCON2bits.VCFG = 0b000;  // tension de referencia Avdd y Avss
}

// Auxiliary function for converting 1.15 radix point to IEEE floating point variable (needed for sqrt).
float Fract2Float( int input )  {
    if ( input < 0 )
        input = - input;
    return ( input / 32768. );
}

// Analiza los componentes de la FFT para luego publicar el resultado en los puertos RB0-RB5
// Las muestras "Samples" contiene la secuencia Re, Im, Re, Im...
void obtenerResultado() {
    unsigned Re, Im, k, max;
    unsigned i = 0;  // Solo como indice para ir avanzando sobre InputSamples
    float    ReFloat, ImFloat, amplitud;

    // La k corresponde al componente, k=0 para la continua, k=1 para 100 Hz,
    // k=2 para 200 Hz, etc. hasta k=63 para 6300 Hz
    k = 0;
    max = 0;  // Almacena el valor maximo de la amplitud de la muestra DFT
    freq = 0;  // Reset current max. frequency for new reading

    // 63 ciclos porque no podria muestrear mas de 63 * 100 Hz = 6300 Hz
    // (que es la mitad de la frecuencia de muestreo)
    while ( k < ( CANT_MUESTRAS / 2 ) )  {
        Re = InputSamples[ i++ ];  // Parte Real de la muestra DFT
        Im = InputSamples[ i++ ];  // Parte Imaginaria de la muestra DFT

        ReFloat = Fract2Float( Re );  // Conversion a float
        ImFloat = Fract2Float( Im );  // Conversion a float

        // Amplitud de la actual muestra DFT
        amplitud = sqrt( ReFloat * ReFloat + ImFloat * ImFloat );

        // DFT esta en escala 1/amplitud, por eso lo volvemos a escala
        amplitud  = amplitud * CANT_MUESTRAS;
        
        magnitudFrecuencias[ k ] = amplitud;

        if ( k == 0 )
            amplitud = 0;  // Elimina la continua

        if ( amplitud > max ) {
            max = amplitud;  // Almacenamos el valor maximo hasta ahora
            freq = k;  // Almacenamos el componente con mayor potencia
        }

        // Avanzamos de a un componente.
        // En este caso, nos desplzamos 100 Hz cada vez que incrementamos k
        k++;
    }

    // Con esta linea freq tomaria los valores en Hz de la frecuencia con mas potencia.
//    freq *= (FREC_MUESTREO / CANT_MUESTRAS);

    // Desplegamos el valor en los puertos RB0-RB5
    LATBbits.LATB5 = ( freq & 0b0000000000100000 ) >> 5;
    LATBbits.LATB4 = ( freq & 0b0000000000010000 ) >> 4;
    LATBbits.LATB3 = ( freq & 0b0000000000001000 ) >> 3;
    LATBbits.LATB2 = ( freq & 0b0000000000000100 ) >> 2;
    LATBbits.LATB1 = ( freq & 0b0000000000000010 ) >> 1;
    LATBbits.LATB0 = ( freq & 0b0000000000000001 ) >> 0;
    
//    if ( freq != freq_old )  {
//        UART1_Write_Text( "Frecuencia = " );
//        IntToStr( freq, uart_wr );  // Tener en cuenta que rellane con espacios hasta llegar a 7 chars
//        UART1_Write_Text( uart_wr );
//        UART1_Write( 10 );
//        UART1_Write( 13 );
//    }
    
    // A continuacion para el envio de los valores de todas las frecuencias
    // Para comenzar se envia || y para terminar tambien ||
    k = 0;

    UART1_Write_Text( "Inicio" );

    while ( k < ( CANT_MUESTRAS / 2 ) )  {
        UART1_Write( magnitudFrecuencias[ k ] );
        k++;
    }

    UART1_Write_Text( "Fin" );

    LATBbits.LATB11 = !LATBbits.LATB11;  // Cada vez que se publica el resultado

//    freq_old = freq;  // freq_old la usamos para actualizar o no lo que se envia al UART, para no repetir los mensajes enviados.
}

unsigned leerAdc()  {
    ADCON1bits.SAMP = 1;  // Pedimos una muestra
    asm nop;  // Tiempo que debemos esperar para que tome una muestra
    ADCON1bits.SAMP = 0;  // Pedimos que retenga la muestra

    return ADCBUF0;  // Devolvemos el valor muestreado por el ADC
}

// Llena Samples con las muestras en Re y Im se pone en 0. Luego copia en el bloque de memoria Y
void SampleInput()  {
    Samples[ globali++ ] = leerAdc();   // Re
    Samples[ globali++ ] = 0;           // Im

    LATFbits.LATF1 = !LATFbits.LATF1;  // En este puerto se puede ver la frecuencia de muestreo

    // Entra a este if cuando ya tiene 128 pares.
    if ( globali >= ( CANT_MUESTRAS * 2 ) )  {
        globali = 0;
        if ( ! listo )  {  // Todavia no tenemos suficientes muestras

            // Copiamos las muestras del ADC hacia el bloque de memoria Y
            memcpy( InputSamples, Samples, CANT_MUESTRAS * 2 );

            // Ya estamos listos para aplicar FFT.
            // Esto habilita el uso de la funcion FFT en la funcion main()
            listo = 1;
        }
    }
}

void  configuracionPuertos()  {
    TRISFbits.TRISF1 = 0;  // Debug frec de muestreo
    TRISBbits.TRISB11 = 0;  // Debug cada vez que se publica el resultado

    // Lo siguientes puertos para mostrar la frecuencia con mayor potencia
    TRISBbits.TRISB0 = 0;
    TRISBbits.TRISB1 = 0;
    TRISBbits.TRISB2 = 0;
    TRISBbits.TRISB3 = 0;
    TRISBbits.TRISB4 = 0;
    TRISBbits.TRISB5 = 0;

    TRISBbits.TRISB7 = 1;  // AN7 para entrada analogica

}

void detectarT2() org 0x0020  {
    SampleInput();  // Se encarga de tomar las muestras
    IFS0bits.T2IF = 0;  // Bandera Timer 2
}

void configuracionT2()  {
    PR2 = ( unsigned long )( Get_Fosc_kHz() ) * 1000 / ( 4 * FREC_MUESTREO );
    IEC0bits.T2IE = 1;  // Habilitamos interrucion del Timer 2
}

void main()  {

    UART1_Init(9600);              // Initialize UART module at 9600 bps
    Delay_ms(100);                 // Wait for UART module to stabilize

//    UART1_Write_Text("Programa iniciado!!!");
//    UART1_Write(10);
//    UART1_Write(13);


    // Ponemos en cero el buffer para las muestras
    memset( InputSamples, 0, CANT_MUESTRAS * 2 );
  
    // Ponemos en cero el array que contendra las magnitudesd e todas las frecuencias
    memset( magnitudFrecuencias, 0, CANT_MUESTRAS / 2 );

    configuracionPuertos();

    configuracionT2();
    T2CONbits.TON = 1;  // Encendemos Timer 2

    configuracionADC();
    ADCON1bits.ADON = 1;  // Encendemos el ADC

    while ( 1 )  {
        if ( listo ) {
            // Calcula FFT en 7 etapas, 128 pares de muestras almacenados en InputSamples.
            FFT( 7, TwiddleCoeff_128, InputSamples );

            // Necesario para acomodar en orden natural los bits.
            BitReverseComplex( 7, InputSamples );

            obtenerResultado();  // Analiza la amplitud de las muestras DFT y publica resultados en RB0-RB5

            listo = 0;  // Indicamos que publicamos un resultado y ahora esperamos el proximo analisis
        }
        
//        if (UART1_Data_Ready()) {     // If data is received,
//            uart_rd = UART1_Read();     // read the received data,
//            UART1_Write(uart_rd);       // and send data via UART
//        }

    }
}
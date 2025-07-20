%Input contingency data file

% expname: experiment label that will be used for naming the output file
expname='exp1';

% datacont: experimental conditions and causal direction index
% a: C, E
% b: C, not-E
% c: not-C, E
% d: not-C, not-E
% causal direction: 1: generative; -1: preventive; 0: unknown
datacont = [8 0 0 8 1  
            8 0 2 6 1 
            16 48 0 64 1
            12 4 16 0 -1
            0 16 4 12 -1
            4 12 16 0 -1];

human=[0.8458    0.6926    0.4355   0.292	0.625	0.917]*100;
humanste = [0.0336    0.0966    0.0871    0.095	0.101	0.058]*100;
condsort = [1 2 3 4 5 6];
        
        
% GenProv: causal direction, 1: generative; -1: preventive; 0: unknown
% master_n_m: sample size N(c-)
% master_n: sample size N(c-) N(c+)
% master_obsprobec: N(e+|c+)
% master_obsprobe_c: N(e+|c-)
master_n_m = [datacont(:,3)+datacont(:,4) ];    
master_n = [datacont(:,3)+datacont(:,4) datacont(:,1)+datacont(:,2)];
master_obsprobe_c = round(datacont(:,3));
master_obsprobec = round(datacont(:,1));
GenProv = datacont(:,5)'; % 1: generative; -1: preventive; 0: causal direction is unknown




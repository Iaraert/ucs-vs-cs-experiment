% The main program including causal support and causal strength using both
% SS prior and Unif prior

clear all;

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%%%%%%%%%%%%%%%%%    Task & Model setup   %%%%%%%%%%%%%%%%%%%%%%%%%%%%
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

taskflag = 1; % 1: support estimate; 2: strength estimate
intflag =0;  % 0: numerical integration (numerical integration precision can be controled, see detailed comments in supanalypriorsim.m); 
              % 1: analytic integration using symbolic toolbox (slow with large sample size (n>40) )

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%%%%%%%%%%%%%%%%%    Input contingency data file %%%%%%%%%%%%%%%%%%%%%
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

%% input data file
exp1data;  % include human ratings in a structural question
% exp2data_str;   % include human ratings in a strength question

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%%%%%%%%%%%%%%%%%    Model parameter setup   %%%%%%%%%%%%%%%%%%%%%%%%%%%%
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%% two parameters in the SS+ prior model
%% alpha is the parameter for SS prior, beta is the parameter for S+ prior
if taskflag==1
	alpha = 5;
	beta = 20; % 20 is for structure judgment with a Yes/No answer; 0: no such a sufficient preference
else
	alpha = 5;
	beta = 0; % 20 is for structure judgment with a Yes/No answer; 0: no such a sufficient preference   
end;
plotflag = 0;  %  1: save prior figure; 0: no figure process (default=0)
bootflag = 0;   % whether to compute a bootstrap confidence interval on the correlation coefficient (default = 0)

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

% read in contingency  conditions
cases1(:,1)=master_obsprobec;                %N(e+,c+), Number of trials where e & c are both present
cases1(:,2)=master_n(:,2)-master_obsprobec;     %N(e-,c+), Number of trials where e is not present but c is
cases1(:,3)=master_obsprobe_c;               %N(e+,c-), Number of trials where e is present but c is not
cases1(:,4)=master_n(:,1)-master_obsprobe_c;    %N(e-,c-), Number of trials where neither e or c is present

for i=1:size(cases1,1)
    cases(i,1) = cases1(condsort(i),1);
    cases(i,2) = cases1(condsort(i),2);
    cases(i,3) = cases1(condsort(i),3);
    cases(i,4) = cases1(condsort(i),4);
    master_n_m1(i)=master_n_m(condsort(i));
    master_obsprobec1(i)=master_obsprobec(condsort(i));
    master_obsprobe_c1(i)=master_obsprobe_c(condsort(i));
    humansort(i) = human(condsort(i));
end;

master_n_m=master_n_m1';
master_obsprobec=master_obsprobec1';
master_obsprobe_c=master_obsprobe_c1';
human=humansort;

% chi-square model
[chi2rst] = chi2HLfunc(cases,GenProv,alpha);

% Bayesian model with SS prior
[rstall] = priormain(cases,GenProv,alpha,beta,intflag,plotflag,taskflag);

% Bayesian model with uniform prior
[rstallunif] = priormain(cases,GenProv,0,0,intflag,plotflag,taskflag);


% sort the results following the pre-defined order (just for plotting purpose)
supportNSP=rstall(:,3)'; unifsupport=rstallunif(:,3)';
probG1=rstall(:,1)';  probG0=rstall(:,2)';
probG1unif=rstallunif(:,1)';  probG0unif=rstallunif(:,2)';

w1maxest=rstall(:,4)'; w1mean=rstall(:,5)'; w1ent=rstall(:,6)';
w1maxestunif=rstallunif(:,4)'; w1meanunif=rstallunif(:,5)'; w1entunif=rstallunif(:,6)';

fprintf('\n');
condsort=1:size(human,2);
for i=1:size(human,2)
    humansort(i) = human(condsort(i));

    supportNSPsort(i) = supportNSP(condsort(i));  % rst from the NS prior model
    unifsupportsort(i) = unifsupport(condsort(i));
    chi2rstsort(i) = chi2rst(condsort(i));
    enc(i) = master_obsprobe_c(condsort(i));
    ec(i) = master_obsprobec(condsort(i));
    sampsize(i) = master_n_m(condsort(i));
    Pg1(i) = probG1(condsort(i));
    Pg0(i) = probG0(condsort(i));
    Pg1unif(i) = probG1unif(condsort(i));
    Pg0unif(i) = probG0unif(condsort(i));
	w1meansort(i) =w1mean(condsort(i));
	w1meansortunif(i) =w1meanunif(condsort(i));
    w1maxestsort(i) =w1maxest(condsort(i));
    w1maxestsortunif(i) =w1maxestunif(condsort(i));
end;

% Result plots 
if taskflag==1   % support estimation
    % save the results without transformation in the output mat file
	rawrst=[humansort;supportNSPsort; unifsupportsort; chi2rstsort;enc;ec;sampsize;Pg1;Pg0]';
	save(sprintf('rawrst.%3.1f.%s.mat',alpha,expname),'rawrst');
    rawrstdisp=[humansort; supportNSPsort;unifsupportsort;chi2rstsort]';
    
	% power transform for model predictions (from T&G program, http://cocosci.berkeley.edu/tom/)
    % Bayesian model with SS prior
	predictions{1}.gamma = fminsearch('powertransform',1,[],supportNSPsort,humansort);
	predictions{1}.value = sign(supportNSPsort).*abs(supportNSPsort).^predictions{1}.gamma;
	predictions{1}.r = -powertransform(predictions{1}.gamma,supportNSPsort,humansort);
	predictions{1}.raw = supportNSPsort;
	if bootflag
       predictions{1}.std = bootcheck(predictions{1}.gamma,supportNSPsort,humansort);
	end
	
    % Bayesian model with Unif prior
	predictions{2}.gamma = fminsearch('powertransform',1,[],unifsupportsort,humansort);
	predictions{2}.value = sign(unifsupportsort).*abs(unifsupportsort).^predictions{2}.gamma;
	predictions{2}.r = -powertransform(predictions{2}.gamma,unifsupportsort,humansort);
	predictions{2}.raw = unifsupportsort;
	if bootflag
       predictions{2}.std = bootcheck(predictions{2}.gamma,unifsupportsort,humansort);
	end
	
    % Chi-square model
	predictions{3}.gamma = fminsearch('powertransform',1,[],chi2rstsort,humansort);
	predictions{3}.value = sign(chi2rstsort).*abs(chi2rstsort).^predictions{3}.gamma;
	predictions{3}.r = -powertransform(predictions{3}.gamma,chi2rstsort,humansort);
	predictions{3}.raw = chi2rstsort;
	if bootflag
       predictions{3}.std = bootcheck(predictions{3}.gamma,chi2rstsort,humansort);
    end
	
	%linear transformation
	minnumx=min(humansort);
	maxnumx=max(humansort);
	min1=min(predictions{1}.value);
	max1=max(predictions{1}.value);
	priormod = (maxnumx-minnumx)/(max1-min1)*(predictions{1}.value-min1)+minnumx;
	min1=min(predictions{2}.value);
	max1=max(predictions{2}.value);
	supportmod = (maxnumx-minnumx)/(max1-min1)*(predictions{2}.value-min1)+minnumx;
	min1=min(predictions{3}.value);
	max1=max(predictions{3}.value);
	chi2mod = (maxnumx-minnumx)/(max1-min1)*(predictions{3}.value-min1)+minnumx;
	
    % print the transfered support values in MATLAB window
    disp('Support judgment (without transformation):');
    disp('     Human      SS+      Unif      Chi2');
    disp(rawrstdisp);
    
	transfrst=[humansort; priormod;supportmod;chi2mod]';
    disp('Support judgment (with transformation):');
    disp('     Human      SS+      Unif      Chi2');
    disp(transfrst);
    
    
elseif taskflag==2   % Strength estimation
    supportrst=[supportNSPsort; unifsupportsort; chi2rstsort;enc;ec;sampsize]';
	rawstrrst=[humansort;w1meansort; w1meansortunif; w1maxestsort;w1maxestsortunif; enc;ec;sampsize]';
	save(sprintf('rawstrrst.%3.1f.%s.mat',alpha,expname),'rawstrrst');
    
    % print the estimated strength values in MATLAB window
 	strmean=[humansort; w1meansort; w1meansortunif]';  %w1maxestsort;w1maxestsortunif ]';
    
    disp('Strength judgment (mean):');
    disp('     Human     SS      Unif   ');
    disp(strmean);
    
end;
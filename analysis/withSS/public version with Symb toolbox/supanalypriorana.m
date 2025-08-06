% This program computes the causal support/strength for a set of
% observations using analytic integration in symbolic toolbox

% Likelihood: a noisy-or model for generative case and noise-and-not for
% preventive case
% Prior: SS generic prior or Unif prior


function [logsupport,probg1,probg0,strengest]=supanalypriorana(GenProv,ptemp,beta,cases,plotflag,taskflag);

numcase=size(cases,1);
genlogsupport=0;
prevlogsupport=0;

if size(GenProv,2)==1 & size(GenProv,1)==1 
    GenProv = ones(1,numcase)*GenProv;
end;

for i = 1:numcase
    strengest(i,1)=0;
    strengest(i,2)=0;
    strengest(i,3)=0;
    fprintf('i=%d  ',i);
    maple restart;
    syms b c ;  % b=1-w0; c=1-w1; a=alpha

    %E is effect & C is candidate cause
    ec = cases(i,1);                            %Number of trials where e & c are both present
    nec = cases(i,2);                           %Number of trials where e is not present but c is
    enc = cases(i,3);                           %Number of trials where e is present but c is not
    nenc = cases(i,4);                          %Number of trials where neither e or c is present
    
    if GenProv(i) ==1 |  GenProv(i) == 0                              %  generative causal direction
       % peak (0,1), (1,0);
       % b=1-w0; c=1-w1   
        prioreq=exp(-beta*(c))*(exp(-ptemp*(1-b)-ptemp*c)+exp(-ptemp*b-ptemp*(1-c)));
        cnormprior = double(int(int(prioreq,c,0,1),b,0,1));

        % this operation below is just for the sake of speek up the
        % computation
        if enc>ec
            fall = expand((1-b)^enc);
            fall2 = b^(nec+nenc)*c^nec*(1-b*c)^ec*prioreq;
            [h11, signloc, terms]=likedistcal2(fall, fall2);
        else
            fall = expand((1-b*c)^ec);
            fall2 = b^(nec+nenc)*c^nec*(1-b)^enc*prioreq;
            [h11, signloc, terms]=likedistcal2(fall, fall2);
        end;
        probGbc_e=(double(h11))/(cnormprior);
        probGbc_e=probGbc_e*nchoosekHL(enc+nenc,enc)*nchoosekHL(ec+nec,ec);
        
        % graph0        
        if ptemp~=0
            priorBE=(1-exp(-ptemp))*exp(-ptemp*(1-b))/ptemp+(1-exp(-ptemp))*exp(-ptemp*b)/ptemp;
            bnormprior = double(int(priorBE,b,0,1));
        else
            priorBE=1;
            bnormprior=1;
        end;
        
        probGb_e = double(int((b^(nec+nenc)*(1-b)^(ec+enc))*priorBE,b,0,1))/bnormprior;
        scale0=nchoosekHL(enc+nenc,enc)*nchoosekHL(ec+nec,ec);
        probGb_e=probGb_e*(scale0);    

        probG1=probGbc_e;  
        probGbc_eGen=probG1;   probGb_eGen=probGb_e; 
        probG0=probGb_e;
        gensupport(i) = probG1/(probG0); 
        probg1(i) = probG1;
        probg0(i) = probG0;
        logsupport(i) = log(gensupport(i));
        fprintf('%d  %d  %d, bc_e=%e  b_e=%e  %12.8f  %e %e\n',enc,ec, ec+nec,probGbc_e/(probGbc_e+probGb_e),...
            probGb_e/(probGbc_e+probGb_e) ,logsupport(i),probG0,probG1);
    end;

    if GenProv(i) == -1 | GenProv(i) == 0                             % preventive causal direction
        % peak at (1,1) --- w0, w1; 
        % b=w0; c=1-w1
        prioreq=exp(-beta*(c))*(exp(-ptemp*(1-b)-ptemp*c)+exp(-ptemp*(1-b)-ptemp*(1-c)));
        cnormprior = double(int(int(prioreq,c,0,1),b,0,1));
        

        if nenc>nec
            fall = expand((1-b)^nenc);
            fall2 = b^(ec+enc)*c^ec*(1-b*c)^nec*prioreq;
            [h11, signloc, terms]=likedistcal2(fall, fall2);
        else
            fall = expand((1-b*c)^nec);
            fall2 = b^(ec+enc)*(1-b)^nenc*c^ec*prioreq;
            [h11, signloc, terms]=likedistcal2(fall, fall2);
        end;
               
%         h11 = int(int(expand(b^(ec+enc)*(1-b)^nenc*c^ec*(1-b*c)^nec*exp(-ptemp*c-ptemp*(1-b))),b,0,1), c, 0, 1);
        probGbc_e=double(h11)/(cnormprior);
        probGbc_e=probGbc_e*nchoosekHL(enc+nenc,enc)*nchoosekHL(ec+nec,ec);

        % graph 0 
        if ptemp~=0
            priorBE=(1-exp(-ptemp))*exp(-ptemp*(1-b))/ptemp;
            bnormprior = double(int(priorBE,b,0,1));
        else
            priorBE=1;
            bnormprior=1;
        end;
        probGb_e = double(int((b^(ec+enc)*(1-b)^(nec+nenc))*priorBE,b,0,1))/bnormprior;
        scale0=nchoosekHL(enc+nenc,enc)*nchoosekHL(ec+nec,ec);
        probGb_e=probGb_e*(scale0);    


        probG1=probGbc_e;  
        probGbc_ePrev=probGbc_e;  probGb_ePrev=probGb_e;
        probG0=probGb_e;
        gensupport(i) = probG1/(probG0); 
        probg1(i) = probG1;
        probg0(i) = probG0;
        logsupport(i) = log(gensupport(i));
        fprintf('%d  %d  %d, bc_e=%e  b_e=%e  %12.8f  %e %e\n',enc,ec, ec+nec,probGbc_e/(probGbc_e+probGb_e),...
            probGb_e/(probGbc_e+probGb_e) ,logsupport(i),probG0,probG1);
    end;
        
    if GenProv(i) == 0          % causal direction is unknown
        ProbGraph(1)= probGbc_eGen/(probGbc_eGen+probGbc_ePrev);
        ProbGraph(2)= probGbc_ePrev/(probGbc_eGen+probGbc_ePrev);
        logsupport(i) = (probGbc_eGen+probGbc_ePrev)/(probGb_eGen+probGb_ePrev);
    end  
    
    %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%% 
    %% estimate causal strength
    %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
    if taskflag==2 
        if GenProv(i) == 1  % generative  % peak at (0,1) and (1,0)
            eq=exp(-ptemp*(1-b)-ptemp*c)+exp(-ptemp*b-ptemp*(1-c));
            cnormprior = double(int(int(eq,b,0,1),c,0,1));
            prioreq = eq/cnormprior;
            
            likelieq = b^enc*(1-b)^nenc*((1-b)*(1-c))^nec*(1-(1-b)*(1-c))^ec*nchoosekHL(enc+nenc,enc)*nchoosekHL(ec+nec,ec);
            
            probdist1 = int(prioreq*likelieq, b, 0,1);
            normterm= double(int(probdist1,c,0,1));            
            w1mean = int(c*probdist1, c, 0,1)/normterm;            
           
        elseif  GenProv(i) == -1  % preventive    % peak at (1,1) and (1,0)
            eq=exp(-ptemp*(1-b)-ptemp*(1-c))+exp(-ptemp*(1-b)-ptemp*(c));
            cnormprior = double(int(int(eq,c,0,1),b,0,1));
            prioreq = eq/cnormprior;
            
            likelieq = b^enc*(1-b)^nenc*(1-b*(1-c))^nec*(b*(1-c))^ec*nchoosekHL(enc+nenc,enc)*nchoosekHL(ec+nec,ec);
            
            probdist1 = int(prioreq*likelieq, b, 0,1);
            normterm= double(int(probdist1,c,0,1));            
            w1mean = int(c*probdist1, c, 0,1)/normterm;   
          
               
        elseif GenProv(i) == 0   % causal direction unknown 
            for jj=1: 2
                if jj==1
                    eq=exp(-ptemp*(1-b)-ptemp*c)+exp(-ptemp*b-ptemp*(1-c));
                    cnormprior = double(int(int(eq,b,0,1),c,0,1));
                    prioreq = eq/cnormprior;

                    likelieq = b^enc*(1-b)^nenc*((1-b)*(1-c))^nec*(1-(1-b)*(1-c))^ec*nchoosekHL(enc+nenc,enc)*nchoosekHL(ec+nec,ec);

                    probdist1 = int(prioreq*likelieq, b, 0,1);
                    normterm= double(int(probdist1,c,0,1));            
                    w1mean0(jj) = int(c*probdist1, c, 0,1)/normterm;                        
                    
                elseif jj==2
                    eq=exp(-ptemp*(1-b)-ptemp*(1-c))+exp(-ptemp*(1-b)-ptemp*(c));
                    cnormprior = double(int(int(eq,c,0,1),b,0,1));
                    prioreq = eq/cnormprior;

                    likelieq = b^enc*(1-b)^nenc*(1-b*(1-c))^nec*(b*(1-c))^ec*nchoosekHL(enc+nenc,enc)*nchoosekHL(ec+nec,ec);

                    probdist1 = int(prioreq*likelieq, b, 0,1);
                    normterm= double(int(probdist1,c,0,1));            
                    w1mean0(jj) = int(c*probdist1, c, 0,1)/normterm;                      
                    
                end;                
            end;
             w1mean=ProbGraph(1)*w1mean0(1)-ProbGraph(2)*w1mean0(2);
            
 
        end;
        
        
%         w0est=0.5; w1est=0.5;
%         interval=0.005;
%         tiw0 = max(0,w0est-2000*interval):interval:min(1,w0est+2000*interval); 
%         tiw1 = max(0,w1est-2000*interval):interval:min(1,w1est+2000*interval); 
%         [w0,w1] = meshgrid(tiw0,tiw1);
% 
%         postprobeq=likelieq*prioreq;                
%         postprob = double(subs(postprobeq,{b,c},{w0,w1}));
% 
%       
%         postprobw0=sum(postprob)/(sum(sum(postprob))*interval);   %  w0 distribution
%         postprobw1=sum(postprob')/(sum(sum(postprob))*interval);   % w1 distribution
%         postprobw1=postprobw1/sum(postprobw1);
%         
%         PostG1 = probG1/(probG0+probG1); 
%         PostG0 = 1-PostG1;
%         
%         [w0estind, w1estind]=find(postprobw1==max(max(postprobw1)));
%         w1maxest=tiw1(w1estind);
%         w1mean = sum(postprobw1.*tiw1);
%         w1ent = entropyhl(postprobw1);

        strengest(i,1)=0;%w1maxest;
        strengest(i,2)=w1mean;
        strengest(i,3)=0;%w1ent;
    else
        strengest(i,1)=0;
        strengest(i,2)=0;
        strengest(i,3)=0;
    end;
end    

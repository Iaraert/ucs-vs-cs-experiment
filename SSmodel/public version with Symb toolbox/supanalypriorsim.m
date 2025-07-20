% This program computes the causal support/strength for a set of observations using numerical integration

% Likelihood: a noisy-or model for generative case and noise-and-not for preventive case 
% Prior: NS generic prior and Unif prior
% intprecision controls the precision of numerical integration. see comments on line 10

function [logsupport,probg1,probg0,strengest]=supanalypriorsim(GenProv,ptemp,beta,cases,plotflag,taskflag,linearflag)

intprecision = 1.0e-16; %1.0e-20(recommend it if your computer is fast enough);  % a smaller value indicates more precision but could need more computing time

numcase=size(cases,1);
syms b c a;  % b=1-w0; c=1-w1; a: alpha
genlogsupport=0;
prevlogsupport=0;

[fx, fy]=meshgrid(0:1/100:1);

logsupport=zeros(1,numcase);
probg1=zeros(1,numcase);
probg0=zeros(1,numcase);

if size(GenProv,2)==1 & size(GenProv,1)==1 
    GenProv = ones(1,numcase)*GenProv;
end;

for i = 1:numcase;                              %E is effect & C is candidate cause
    ec = cases(i,1);                            %Number of trials where e & c are both present
    nec = cases(i,2);                           %Number of trials where e is not present but c is
    enc = cases(i,3);                           %Number of trials where e is present but c is not
    nenc = cases(i,4);                          %Number of trials where neither e or c is present
      
    if GenProv(i) == 1  | GenProv(i) == 0                         %  generative causal direction
        % peak (0,1), (1,0);
        % w0: x, b; w1: y, c;
            Pd1_w=sprintf('x.^%d.*(1-x).^%d',enc,nenc);
            Pd2_w=sprintf('((1-x).*(1-y)).^%d.*(1-(1-x).*(1-y)).^%d',nec,ec);

            
        eq=exp(-beta*(1-c))*(exp(-ptemp*(1-b)-ptemp*c)+exp(-ptemp*b-ptemp*(1-c)));
        cnormprior = double(int(int(eq,b,0,1),c,0,1));
        prioreq = eq/cnormprior;
        priorG1=sprintf('(exp(-%f*(1-y)).*(exp(-%f*(1-y)-%f*x)+exp(-%f*y-%f*(1-x))))',...
            beta,ptemp,ptemp,ptemp,ptemp);
        
        str1=strcat(Pd1_w,'.*',Pd2_w,'.*',priorG1); 
        probGbc_e=nchoosekHL(enc+nenc,enc)*nchoosekHL(ec+nec,ec)*dblquad(inline(str1),0,1,0,1,intprecision,@quadl)/cnormprior;
       
        %graph0 
        pd0=sprintf('x.^(%d+%d).*(1-x).^(%d+%d)',enc,ec,nenc,nec);
        if ptemp~=0 
            bpriorf = exp(-ptemp*b)*(1-exp(-ptemp))/ptemp+exp(-ptemp*(1-b))*(1-exp(-ptemp))/ptemp;
            bnormprior = double(int(bpriorf,b,0,1));
            priorG0=sprintf('(exp(-%f*x)*(1-exp(-%f))/%f+exp(-%f*(1-x))*(1-exp(-%f))/%f)',...
                ptemp,ptemp,ptemp,ptemp,ptemp,ptemp);    
            str0=strcat(pd0,'.*',priorG0);
        else
            bnormprior = 1;
            str0=strcat(pd0);
        end;

        probGb_e=nchoosekHL(enc+nenc,enc)*nchoosekHL(ec+nec,ec)*quadl(inline(str0),0,1,intprecision)/bnormprior;

        probG1=probGbc_e;
        probG0=probGb_e;
        gensupport(i) = probG1/probG0; 
        probg1(i) = probG1;
        probg0(i) = probG0;
        logsupport(i) = log(gensupport(i)); 
	
        fprintf('%d  %d  %d, bc_e=%e  b_e=%e  %12.8f  %e %e\n',enc,ec, ec+nec,probGbc_e/(probGbc_e+probGb_e),...
            probGb_e/(probGbc_e+probGb_e) ,logsupport(i),probG0,probG1);
        if GenProv(i) == 0 
            probGbc_eGen=probG1;     
            probGb_eGen=probG0;     
        end;
    end;
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
    
    if GenProv(i) == -1  |  GenProv(i) == 0                          % preventive causal direction
        % peak (1,1), (1,0);
        % w0: x, b; w1: y, c;
        Pd1_w=sprintf('x.^%d.*(1-x).^%d',enc,nenc);
        Pd2_w=sprintf('(1-(x).*(1-y)).^%d.*(x.*(1-y)).^%d',nec,ec);
        likelieq = b^enc*(1-b)^nenc*(1-b*(1-c))^nec*(b*(1-c))^ec;
 
        eq=exp(-beta*(1-c))*(exp(-ptemp*(1-b)-ptemp*c)+exp(-ptemp*(1-b)-ptemp*(1-c)));
        cnormprior = double(int(int(eq,c,0,1),b,0,1));
        priorG1=sprintf('(exp(-%f*(1-y)).*(exp(-%f*(1-x)-%f*y)+exp(-%f*(1-x)-%f*(1-y))))', beta, ptemp,ptemp,ptemp,ptemp);
        prioreq = eq/cnormprior;        

        str1=strcat(Pd1_w,'.*',Pd2_w,'.*',priorG1);
        probGbc_e=nchoosekHL(enc+nenc,enc)*nchoosekHL(ec+nec,ec)*dblquad(inline(str1),0,1,0,1,intprecision,@quadl)/cnormprior;,
    

        % graph0
        pd0=sprintf('x.^(%d+%d).*(1-x).^(%d+%d)',enc,ec,nenc,nec);
        if ptemp~=0 
            bpriorf=(exp(-ptemp*(1-b)) );
            bnormprior = double(int(bpriorf,b,0,1));
            priorG0=sprintf('(exp(-%f*(1-x)))',ptemp);
            str0=strcat(pd0,'.*',priorG0);
        else
            bpriorf = exp(-ptemp*(1-b));
            bnormprior=1;
            str0=strcat(pd0);
        end;

        probGb_e=nchoosekHL(enc+nenc,enc)*nchoosekHL(ec+nec,ec)*quadl(inline(str0),0,1,intprecision)/bnormprior;

        
        probG1=probGbc_e;
        probG0=probGb_e;
        gensupport(i) = probG1/(probG0); 
        probg1(i) = probG1;
        probg0(i) = probG0;
        logsupport(i) = log(gensupport(i)); 
            
        fprintf('%d  %d  %d, bc_e=%e  b_e=%e  %12.8f  %e %e\n',enc,ec, ec+nec,probGbc_e/(probGbc_e+probGb_e),...
            probGb_e/(probGbc_e+probGb_e) ,logsupport(i),probG0,probG1);
        
        if GenProv(i) == 0 
            probGbc_ePrev=probG1;   
            probGb_ePrev=probG0;  
        end;
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
        interval=0.0005;
        tiw0 = 0:interval:1; 
        tiw1 = 0:interval:1; 
        [w0,w1] = meshgrid(tiw0,tiw1);
        if GenProv(i) == 1  % generative  % peak at (0,1) and (1,0)
            eq=exp(-ptemp*(1-b)-ptemp*c)+exp(-ptemp*b-ptemp*(1-c));
            cnormprior = double(int(int(eq,b,0,1),c,0,1));
            prioreq = eq/cnormprior;
            priorG1=sprintf('((exp(-%f*(1-y)-%f*x)+exp(-%f*y-%f*(1-x))))/%f',ptemp,ptemp,ptemp,ptemp,cnormprior);
        elseif GenProv(i) == -1  % preventive    % peak at (1,1) and (1,0)
            eq=exp(-ptemp*(1-b)-ptemp*(1-c))+exp(-ptemp*(1-b)-ptemp*(c));
            cnormprior = double(int(int(eq,c,0,1),b,0,1));
            priorG1=sprintf('(exp(-%f*(1-x)-%f*(1-y))+exp(-%f*(1-x)-%f*(y)))/%f', ptemp,ptemp, ptemp,ptemp,cnormprior);
            prioreq = eq/cnormprior;            
        end;
        
        if GenProv(i) == 0  %causal direction is unknown
            % strength calculation
            for jj=1:2
                if jj == 1  % generative  % peak at (0,1) and (1,0)
                    eq=exp(-ptemp*(1-b)-ptemp*c)+exp(-ptemp*b-ptemp*(1-c));
                    cnormprior = double(int(int(eq,b,0,1),c,0,1));
                    priorprob2 = exp(-ptemp*(1-w0)-ptemp*w1)+exp(-ptemp*w0-ptemp*(1-w1));
                    priorprob2 = priorprob2/cnormprior;               
                    likeliprob2 = nchoosekHL(enc+nenc,enc)*nchoosekHL(ec+nec,ec)*(w0.^enc).*((1-w0).^nenc).*(((1-w0).*(1-w1)).^nec).*((1-(1-w0).*(1-w1)).^ec);
 
                elseif jj == 2  % preventive    % peak at (1,1) and (1,0)
                    eq=exp(-ptemp*(1-b)-ptemp*(1-c))+exp(-ptemp*(1-b)-ptemp*(c));
                    cnormprior = double(int(int(eq,c,0,1),b,0,1));
                    priorG1=sprintf('(exp(-%f*(1-x)-%f*(1-y))+exp(-%f*(1-x)-%f*(y)))/%f', ptemp,ptemp, ptemp,ptemp,cnormprior);
                    prioreq = eq/cnormprior;    
                    priorprob2 = exp(-ptemp*(1-w0)-ptemp*w1)+exp(-ptemp*(1-w0)-ptemp*(1-w1));
                    priorprob2 = priorprob2/cnormprior;

                    likeliprob2 = nchoosekHL(enc+nenc,enc)*nchoosekHL(ec+nec,ec)*w0.^enc.*(1-w0).^nenc.*(1-w0.*(1-w1)).^nec.*(w0.*(1-w1)).^ec;
                end;
                
                postprob=likeliprob2.*priorprob2;   
                postprobw1=sum(postprob')/(sum(sum(postprob))*interval);   % w1 distribution 
                postprobw1=postprobw1/sum(postprobw1);
                
                % plot(tiw1,postprobw1);
                [w0estind, w1estind]=find(postprobw1==max(max(postprobw1)));
                w1maxest0(jj)=tiw1(w1estind(1));
                w1mean0(jj) = sum(postprobw1.*tiw1);
                w1ent0(jj) = 0;%entropyhl(postprobw1);
            end;
            % weighted average
            meanws(i,2)=ProbGraph(1)*w1mean0(1)-ProbGraph(2)*w1mean0(2);
            strengest(i,2)=ProbGraph(1)*w1maxest0(1)-ProbGraph(2)*w1maxest0(2);
            entropy(i,2)=0;
            varws(i,2)=0;
            postprobw0(:,:,i)=sum(postprobw1)/(sum(sum(postprobw1)));%*interval
            postprobw11(:,:,i)=sum(postprobw1')/(sum(sum(postprobw1)));%*interval    
            
            strengest(i,1)=strengest(i,2);
            strengest(i,2)=meanws(i,2);
            strengest(i,3)=entropy(i,2);            
        else
            if GenProv(i) == 1  % generative  % peak at (0,1) and (1,0)
                eq=exp(-ptemp*(1-b)-ptemp*c)+exp(-ptemp*b-ptemp*(1-c));
                cnormprior = double(int(int(eq,b,0,1),c,0,1));
                priorprob2 = exp(-ptemp*(1-w0)-ptemp*w1)+exp(-ptemp*w0-ptemp*(1-w1));
                priorprob2 = priorprob2/cnormprior;               
                    likeliprob2 = nchoosekHL(enc+nenc,enc)*nchoosekHL(ec+nec,ec)*(w0.^enc).*((1-w0).^nenc).*(((1-w0).*(1-w1)).^nec).*((1-(1-w0).*(1-w1)).^ec);
                 
            elseif GenProv(i) == -1  % preventive    % peak at (1,1) and (1,0)
                eq=exp(-ptemp*(1-b)-ptemp*(1-c))+exp(-ptemp*(1-b)-ptemp*(c));
                cnormprior = double(int(int(eq,c,0,1),b,0,1));
                priorG1=sprintf('(exp(-%f*(1-x)-%f*(1-y))+exp(-%f*(1-x)-%f*(y)))/%f', ptemp,ptemp, ptemp,ptemp,cnormprior);
                prioreq = eq/cnormprior;    
                 priorprob2 = exp(-ptemp*(1-w0)-ptemp*w1)+exp(-ptemp*(1-w0)-ptemp*(1-w1));
                priorprob2 = priorprob2/cnormprior;
                
                    likeliprob2 = nchoosekHL(enc+nenc,enc)*nchoosekHL(ec+nec,ec)*w0.^enc.*(1-w0).^nenc.*(1-w0.*(1-w1)).^nec.*(w0.*(1-w1)).^ec;
             end;

            postprob=likeliprob2.*priorprob2;                

            
            postprobw0=sum(postprob)/(sum(sum(postprob))*interval);   %  w0 distribution
            postprobw1=sum(postprob')/(sum(sum(postprob))*interval);   % w1 distribution
            postprobw1=postprobw1/sum(postprobw1);
            
            PostG1 = probG1/(probG0+probG1); 
            PostG0 = 1-PostG1;
            
            [w0estind, w1estind]=find(postprobw1==max(max(postprobw1)));
            w1maxest=tiw1(w1estind);
            w1mean = sum(postprobw1.*tiw1);
            if plotflag==1
                plot(tiw1,postprobw1,'--k','LineWidth',3);
            end;                

            strengest(i,1)=w1maxest;
            strengest(i,2)=w1mean;
            strengest(i,3)=0;
        end;
        
    else
        strengest(i,1)=0;
        strengest(i,2)=0;
        strengest(i,3)=0;
    end;
end    

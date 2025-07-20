% run analytic computation on generic prior model 
function [support_gen] =priormain(cases,GenProv,alpha,beta,intflag,plotflag,taskflag)

if intflag==0
    [logsupport,probg1,probg0,strengest]=supanalypriorsim(GenProv,alpha,beta,cases,plotflag,taskflag);
else
    [logsupport,probg1,probg0,strengest]=supanalypriorana(GenProv,alpha,beta,cases,plotflag,taskflag);
end;  

for i=1:size(probg1,2)
    support_gen(i,1)=probg1(i);%/(probg1(i)+probg0(i));
    support_gen(i,2)=probg0(i);%/(probg1(i)+probg0(i));
    support_gen(i,3)=logsupport(i);
    support_gen(i,4)=strengest(i,1);  % max w1
    support_gen(i,5)=strengest(i,2);  % mean w1
    support_gen(i,6)=strengest(i,3);  % entropy w1
end;


% chi-square
function [chi2rst] = chi2HLfunc(cases,GenProv,ptemp,A,B,bootflag);

numcase=size(cases,1);

for i = 1:numcase;                              %E is effect & C is candidate cause
    ec = cases(i,1);                            %Number of trials where e & c are both present
    nec = cases(i,2);                           %Number of trials where e is not present but c is
    enc = cases(i,3);                           %Number of trials where e is present but c is not
    nenc = cases(i,4);                          %Number of trials where neither e or c is present
	
	sum_e = enc+ec;
	sum_ne = nenc+nec;
	sum_nc = enc+nenc;
	sum_c = ec+nec;
	
	N=sum_c+sum_nc;
	
	Menc=sum_e*sum_nc/N;
	Mnenc=sum_ne*sum_nc/N;
	Mec=sum_e*sum_c/N;
	Mnec=sum_ne*sum_c/N;
	
	chi2rst(i) = (enc-Menc)^2/Menc+(nenc-Mnenc)^2/Mnenc+(ec-Mec)^2/Mec+(nec-Mnec)^2/Mnec;
end;
% this program is to decompose the expanded function into separated
% additive terms for applying analytic integration
% integration over b,c.

function [G1prob, signloc, terms]=likedistcal2(fall, fall2)
clear maplemex;
syms b c ;    
    
fallchar = char(expand(fall));

aloc=strfind(char(fallchar),'+');
sloc=strfind(char(fallchar),'-');
signloc0 =[aloc sloc; ones(size(aloc)) -ones(size(sloc))]';
signloc = sortrows(signloc0);

if signloc(1,1)==1
    G1prob=0;
    for si = 1:size(signloc,1)-1
        terms{si}=fallchar(signloc(si,1)+1:signloc(si+1,1)-1);
        eqtemp = sym(maple(terms{si}))*fall2;;
        G1prob=G1prob+signloc(si,2)*(int(int(eqtemp,c,0,1),b,0,1));
    end;
    terms{size(signloc,1)}=fallchar(signloc(size(signloc,1),1)+1:end);
    eqtemp = sym(maple(terms{size(signloc,1)}))*fall2;;
    G1prob=G1prob+signloc(size(signloc,1),2)*(int(int(eqtemp,c,0,1),b,0,1));
else
    G1prob=0;
    terms{1}=fallchar(1:signloc(1,1)-1);
    eqtemp = sym(maple(terms{1}))*fall2;;
    G1prob=(int(int(eqtemp,c,0,1),b,0,1));

    for si = 1:size(signloc,1)-1
        terms{si+1}=fallchar(signloc(si,1)+1:signloc(si+1)-1);
        eqtemp = sym(maple(terms{si+1}))*fall2;
        G1prob=G1prob+signloc(si,2)*(int(int(eqtemp,c,0,1),b,0,1));
    end;
    terms{size(signloc,1)+1}=fallchar(signloc(size(signloc,1),1)+1:end);
    eqtemp = sym(maple(terms{size(signloc,1)+1}))*fall2;;
    G1prob=G1prob+signloc(size(signloc,1),2)*(int(int(eqtemp,c,0,1),b,0,1));
end;
G1prob=double(G1prob);
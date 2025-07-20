% all combinations without considering orders. n!/(n-k)!/k!

function rst=nchoosekHL(n,k)

temp=sum(log(1:n))-sum(log(1:k))-sum(log(1:n-k));
rst = exp(temp);